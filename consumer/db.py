import json
from datetime import datetime, timezone

import psycopg2

from config import settings
from logging_config import get_logger

logger = get_logger(__name__)


def get_connection():
    return psycopg2.connect(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        dbname=settings.POSTGRES_DB,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASS,
    )


def insert_order(conn, order_data: dict) -> bool:
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO orders (correlation_id, customer_id, amount, currency, source_server, status, created_at, processed_at)
        VALUES (%s, %s, %s, %s, %s, 'PROCESSED', %s, %s)
        """,
        (
            order_data["correlation_id"],
            order_data["customer_id"],
            order_data["amount"],
            order_data["currency"],
            order_data.get("source_server"),
            order_data.get("created_at", datetime.now(timezone.utc).isoformat()),
            datetime.now(timezone.utc),
        ),
    )
    conn.commit()
    cur.close()
    logger.info(
        "Order inserted into database",
        extra={"correlation_id": order_data["correlation_id"], "customer_id": order_data["customer_id"]},
    )
    return True


def insert_dead_letter(conn, correlation_id: str, payload: dict, error_message: str, retry_count: int) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO dead_letters (correlation_id, payload, error_message, retry_count)
        VALUES (%s, %s, %s, %s)
        """,
        (correlation_id, json.dumps(payload), error_message, retry_count),
    )
    conn.commit()
    cur.close()
    logger.warning(
        "Dead letter recorded",
        extra={"correlation_id": correlation_id, "retry_count": retry_count, "error": error_message},
    )
