import json
import traceback

from logging_config import correlation_id_var, get_logger
from db import get_connection, insert_order

logger = get_logger(__name__)


def process_message(body: bytes, properties) -> bool:
    cid = getattr(properties, "correlation_id", None) or "-"
    token = correlation_id_var.set(cid)

    try:
        order_data = json.loads(body)
        logger.info(
            "Processing message",
            extra={"correlation_id": cid, "customer_id": order_data.get("customer_id")},
        )

        conn = get_connection()
        try:
            insert_order(conn, order_data)
        finally:
            conn.close()

        logger.info("Message processed successfully", extra={"correlation_id": cid})
        return True

    except Exception as e:
        logger.error(
            "Failed to process message",
            extra={"correlation_id": cid, "error": str(e), "traceback": traceback.format_exc()},
        )
        return False

    finally:
        correlation_id_var.reset(token)
