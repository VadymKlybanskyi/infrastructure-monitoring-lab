import os
import time

import psycopg
from fastapi import FastAPI
from prometheus_client import Counter, Histogram, make_asgi_app

app = FastAPI()

REQUEST_COUNT = Counter(
    "api_requests_total",
    "Total API requests",
    ["method", "endpoint", "status"]
)

REQUEST_LATENCY = Histogram(
    "api_request_duration_seconds",
    "API request duration"
)


@app.middleware("http")
async def monitor_requests(request, call_next):
    start = time.time()

    response = await call_next(request)

    duration = time.time() - start

    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=str(response.status_code)
    ).inc()

    REQUEST_LATENCY.observe(duration)

    return response


app.mount("/metrics", make_asgi_app())


@app.get("/")
def root():
    return {"message": "Infrastructure Monitoring Lab"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/db-check")
def db_check():
    try:
        with psycopg.connect(
            host=os.getenv("DB_HOST", "db"),
            dbname=os.getenv("DB_NAME", "support_lab"),
            user=os.getenv("DB_USER", "lab_user"),
            password=os.getenv("DB_PASSWORD")
        ) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                result = cur.fetchone()

        return {
            "database": "connected",
            "result": result[0]
        }

    except Exception as error:
        return {
            "database": "error",
            "details": str(error)
        }
