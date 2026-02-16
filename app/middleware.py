import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from logging_config import correlation_id_var, get_logger

logger = get_logger(__name__)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        cid = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        token = correlation_id_var.set(cid)

        logger.info(
            "Request started",
            extra={"method": request.method, "path": str(request.url.path)},
        )

        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            raise
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.info(
                "Request completed",
                extra={
                    "method": request.method,
                    "path": str(request.url.path),
                    "status_code": getattr(response, "status_code", 500) if "response" in dir() else 500,
                    "duration_ms": duration_ms,
                },
            )
            correlation_id_var.reset(token)

        response.headers["X-Correlation-ID"] = cid
        return response
