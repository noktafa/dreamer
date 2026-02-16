import random
import time
import traceback
from datetime import datetime, timezone

import pika
import psycopg2
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from config import settings
from logging_config import correlation_id_var, get_logger, setup_logging
from middleware import CorrelationIdMiddleware
from models import HealthResponse, OrderRequest, OrderResponse
from publisher import publish_order

setup_logging()
logger = get_logger(__name__)

app = FastAPI(title="Banking POC API", version="1.0.0")
app.add_middleware(CorrelationIdMiddleware)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    cid = correlation_id_var.get("-")
    logger.error(
        "Unhandled exception",
        extra={"correlation_id": cid, "traceback": traceback.format_exc()},
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "correlation_id": cid},
    )


@app.post("/api/orders", status_code=202, response_model=OrderResponse)
async def create_order(order: OrderRequest):
    cid = correlation_id_var.get("-")
    logger.info(
        "Received order",
        extra={"customer_id": order.customer_id, "amount": order.amount},
    )

    payload = {
        "correlation_id": cid,
        "customer_id": order.customer_id,
        "amount": order.amount,
        "currency": order.currency,
        "source_server": settings.SERVER_NAME,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    success = publish_order(payload, cid)
    if not success:
        raise HTTPException(status_code=503, detail="Failed to queue order")

    return OrderResponse(
        correlation_id=cid,
        status="accepted",
        message="Order queued for processing",
    )


@app.get("/api/orders/{correlation_id}")
async def get_order(correlation_id: str):
    try:
        conn = psycopg2.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            dbname=settings.POSTGRES_DB,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASS,
        )
        cur = conn.cursor()
        cur.execute(
            "SELECT correlation_id, customer_id, amount, currency, status, source_server, created_at, processed_at "
            "FROM orders WHERE correlation_id = %s",
            (correlation_id,),
        )
        row = cur.fetchone()
        cur.close()
        conn.close()

        if not row:
            raise HTTPException(status_code=404, detail="Order not found")

        return {
            "correlation_id": str(row[0]),
            "customer_id": row[1],
            "amount": float(row[2]),
            "currency": row[3],
            "status": row[4],
            "source_server": row[5],
            "created_at": row[6].isoformat() if row[6] else None,
            "processed_at": row[7].isoformat() if row[7] else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to query order", extra={"error": str(e)}, exc_info=True)
        raise HTTPException(status_code=500, detail="Database error")


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    status = "healthy"
    try:
        credentials = pika.PlainCredentials(settings.RABBITMQ_USER, settings.RABBITMQ_PASS)
        params = pika.ConnectionParameters(
            host=settings.RABBITMQ_HOST,
            port=settings.RABBITMQ_PORT,
            virtual_host=settings.RABBITMQ_VHOST,
            credentials=credentials,
            connection_attempts=1,
            socket_timeout=2,
        )
        conn = pika.BlockingConnection(params)
        conn.close()
    except Exception:
        status = "degraded"

    return HealthResponse(
        status=status,
        server=settings.SERVER_NAME,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.post("/api/simulate/error")
async def simulate_error():
    cid = correlation_id_var.get("-")
    error_type = random.choice(["validation", "connection", "timeout"])

    try:
        if error_type == "validation":
            raise ValueError("Simulated validation error")
        elif error_type == "connection":
            credentials = pika.PlainCredentials("bad_user", "bad_pass")
            params = pika.ConnectionParameters(
                host=settings.RABBITMQ_HOST,
                port=settings.RABBITMQ_PORT,
                virtual_host="/nonexistent",
                credentials=credentials,
                connection_attempts=1,
                socket_timeout=2,
            )
            pika.BlockingConnection(params)
        else:
            time.sleep(5)
            raise TimeoutError("Simulated database timeout")
    except Exception as e:
        logger.error(
            "Simulated error",
            extra={"error_type": error_type, "correlation_id": cid},
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={
                "error_type": error_type,
                "detail": str(e),
                "correlation_id": cid,
            },
        )


@app.post("/api/simulate/slow")
async def simulate_slow():
    cid = correlation_id_var.get("-")
    delay = round(random.uniform(2, 10), 2)
    logger.warning("Slow response simulated", extra={"delay_seconds": delay, "correlation_id": cid})
    time.sleep(delay)
    return {"delay_seconds": delay}
