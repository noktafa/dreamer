import json
import signal
import sys
import time

import pika

from config import settings
from db import get_connection, insert_dead_letter
from logging_config import get_logger, setup_logging
from processor import process_message

setup_logging()
logger = get_logger(__name__)

shutdown_requested = False


def signal_handler(signum, frame):
    global shutdown_requested
    logger.info("Shutdown signal received", extra={"signal": signum})
    shutdown_requested = True


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def get_retry_count(properties) -> int:
    if properties.headers and "x-death" in properties.headers:
        deaths = properties.headers["x-death"]
        if deaths:
            return sum(d.get("count", 0) for d in deaths)
    return 0


def on_message(channel, method, properties, body):
    cid = getattr(properties, "correlation_id", None) or "-"
    success = process_message(body, properties)

    if success:
        channel.basic_ack(delivery_tag=method.delivery_tag)
        logger.info("Message ACKed", extra={"correlation_id": cid})
    else:
        retry_count = get_retry_count(properties)
        if retry_count < settings.MAX_RETRIES:
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            logger.warning(
                "Message NACKed with requeue",
                extra={"correlation_id": cid, "retry_count": retry_count},
            )
        else:
            try:
                conn = get_connection()
                try:
                    insert_dead_letter(conn, cid, json.loads(body), "Max retries exceeded", retry_count)
                finally:
                    conn.close()
            except Exception as e:
                logger.error("Failed to insert dead letter", extra={"error": str(e)})

            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            logger.error(
                "Message sent to DLQ",
                extra={"correlation_id": cid, "retry_count": retry_count},
            )


def connect_with_retry():
    while not shutdown_requested:
        try:
            credentials = pika.PlainCredentials(settings.RABBITMQ_USER, settings.RABBITMQ_PASS)
            params = pika.ConnectionParameters(
                host=settings.RABBITMQ_HOST,
                port=settings.RABBITMQ_PORT,
                virtual_host=settings.RABBITMQ_VHOST,
                credentials=credentials,
                heartbeat=600,
            )
            connection = pika.BlockingConnection(params)
            logger.info("Connected to RabbitMQ")
            return connection
        except Exception as e:
            logger.warning(f"RabbitMQ connection failed, retrying in 5s: {e}")
            time.sleep(5)
    return None


def main():
    logger.info("Consumer starting up")

    connection = connect_with_retry()
    if not connection:
        logger.info("Shutdown before connection established")
        sys.exit(0)

    channel = connection.channel()
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue="orders_queue", on_message_callback=on_message)

    logger.info("Waiting for messages on orders_queue")
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        logger.info("Consumer interrupted")
    finally:
        try:
            channel.stop_consuming()
            connection.close()
        except Exception:
            pass
        logger.info("Consumer shut down")


if __name__ == "__main__":
    main()
