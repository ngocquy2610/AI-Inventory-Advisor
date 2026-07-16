"""Request logging, internal-token auth check middleware."""

import time
import logging

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import settings
from app.core.security import verify_service_token

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs request method, path, duration, and status."""

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start
        logger.info(
            "%s %s -> %s (%.3fs)",
            request.method,
            request.url.path,
            response.status_code,
            duration,
        )
        return response


class InternalTokenMiddleware(BaseHTTPMiddleware):
    """Verifies the internal bearer token on all routes except health checks."""

    async def dispatch(self, request: Request, call_next):
        if settings.environment == "development":
            return await call_next(request)

        if request.url.path in ("/health", "/openapi.json", "/docs", "/redoc"):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"error": {"code": "unauthorized", "message": "Missing bearer token"}})

        token = auth_header[len("Bearer "):]
        if not verify_service_token(token):
            return JSONResponse(status_code=401, content={"error": {"code": "unauthorized", "message": "Invalid token"}})

        return await call_next(request)