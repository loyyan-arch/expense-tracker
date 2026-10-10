import logging
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request


logger = logging.getLogger("expense_tracker.requests")


def setup_request_logging(app: FastAPI) -> None:
    @app.middleware("http")
    async def log_request(request: Request, call_next):
        request_id = uuid4().hex
        request.state.request_id = request_id
        started_at = perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (perf_counter() - started_at) * 1000

            logger.exception(
                "request_id=%s method=%s path=%s "
                "status=500 duration_ms=%.2f",
                request_id,
                request.method,
                request.url.path,
                duration_ms,
            )
            raise

        duration_ms = (perf_counter() - started_at) * 1000

        logger.info(
            "request_id=%s method=%s path=%s "
            "status=%s duration_ms=%.2f",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )

        response.headers["X-Request-ID"] = request_id
        return response