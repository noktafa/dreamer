import json
import time
import pika
from config import settings
from logging_config import get_logger

logger = get_logger(__name__)


def publish_order(order_data: dict, correlation_id: str) -> bool:
    try:
        credentials = pika.PlainCredentials(settings.RABBITMQ_USER, settings.RABBITMQ_PASS)
        params = pika.ConnectionParameters(
            host=settings.RABBITMQ_HOST,
            port=settings.RABBITMQ_PORT,
            virtual_host=settings.RABBITMQ_VHOST,
            credentials=credentials,
            connection_attempts=3,
            retry_delay=1,
        )
        connection = pika.BlockingConnection(params)
        channel = connection.channel()

        body = json.dumps(order_data)
        properties = pika.BasicProperties(
            delivery_mode=2,
            correlation_id=correlation_id,
            content_type="application/json",
            timestamp=int(time.time()),
        )

        channel.basic_publish(
            exchange="orders_exchange",
            routing_key="orders",
            body=body,
            properties=properties,
        )

        connection.close()
        logger.info("Order published to RabbitMQ", extra={"correlation_id": correlation_id})
        return True

    except Exception as e:
        logger.error(
            "Failed to publish order to RabbitMQ",
            extra={"correlation_id": correlation_id, "error": str(e)},
            exc_info=True,
        )
        return False
