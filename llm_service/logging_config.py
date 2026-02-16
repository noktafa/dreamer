import logging
import os
import socket
import sys
from contextvars import ContextVar
from pythonjsonlogger import jsonlogger

from config import settings

correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="-")


class CorrelationFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id_var.get("-")
        record.server = socket.gethostname()
        return True


def setup_logging() -> None:
    formatter = jsonlogger.JsonFormatter(
        fmt="%(timestamp)s %(level)s %(correlation_id)s %(server)s %(module)s %(message)s",
        rename_fields={"levelname": "level", "asctime": "timestamp"},
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    stdout_handler.addFilter(CorrelationFilter())
    root_logger.addHandler(stdout_handler)

    log_dir = os.path.dirname(settings.LLM_LOG_PATH)
    if log_dir and os.path.isdir(log_dir):
        file_handler = logging.FileHandler(settings.LLM_LOG_PATH)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(CorrelationFilter())
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
