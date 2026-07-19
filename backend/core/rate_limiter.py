import time

from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class Limiter:
    def __init__(self, requests_limit: int = 100, window_seconds: int = 60):
        self.requests_limit = requests_limit
        self.window_seconds = window_seconds
        # client IP -> list of timestamps
        self.history: dict[str, list[float]] = {}

    def is_allowed(self, client_ip: str) -> bool:
        now = time.time()
        if client_ip in self.history:
            self.history[client_ip] = [
                t for t in self.history[client_ip] if now - t < self.window_seconds
            ]
        else:
            self.history[client_ip] = []

        if len(self.history[client_ip]) >= self.requests_limit:
            return False

        self.history[client_ip].append(now)
        return True


limiter = Limiter()


class RateLimitingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Exclude docs and health checks from rate limiting
        if request.url.path in ("/health", "/docs", "/openapi.json"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        if not limiter.is_allowed(client_ip):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Too Many Requests",
                    "message": "Rate limit exceeded. Please try again later.",
                },
            )
        return await call_next(request)
