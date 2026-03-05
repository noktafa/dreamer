import socket
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "app_user"
    RABBITMQ_PASS: str = ""
    RABBITMQ_VHOST: str = "/banking_poc"

    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "banking_poc"
    POSTGRES_USER: str = "app_user"
    POSTGRES_PASS: str = ""

    CONSUMER_LOG_PATH: str = "/var/log/consumer/consumer.log"
    MAX_RETRIES: int = 3
    SERVER_NAME: str = socket.gethostname()

    model_config = {"env_prefix": ""}


settings = Settings()
