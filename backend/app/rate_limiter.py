"""
Rate limiting for StudentsAI MVP API
"""

import time
from collections import defaultdict, deque
from functools import wraps

from fastapi import HTTPException, Request, status

from .config import DEBUG, RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW, settings


class InMemoryRateLimiter:
    """Simple in-memory rate limiter using sliding window"""

    def __init__(self):
        self.requests: dict[str, deque] = defaultdict(deque)

    def is_allowed(self, key: str, limit: int, window: int) -> bool:
        """Check if request is allowed within rate limit"""
        now = time.time()

        # Clean old requests outside the window
        while self.requests[key] and self.requests[key][0] <= now - window:
            self.requests[key].popleft()

        # Check if under limit
        if len(self.requests[key]) < limit:
            self.requests[key].append(now)
            return True

        return False

    def get_reset_time(self, key: str, window: int) -> float | None:
        """Get time when rate limit resets"""
        if not self.requests[key]:
            return None

        return self.requests[key][0] + window


# Global rate limiter instance
rate_limiter = InMemoryRateLimiter()


def get_client_ip(request: Request) -> str:
    """Get client IP address from request"""
    # Check for forwarded headers (for reverse proxies)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # Fallback to direct client IP
    return request.client.host if request.client else "unknown"


def get_rate_limit_key(request: Request, user_id: str | None = None) -> str:
    """Generate rate limit key based on user or IP"""
    if user_id:
        return f"user:{user_id}"

    client_ip = get_client_ip(request)
    return f"ip:{client_ip}"


async def check_rate_limit(
    request: Request,
    user_id: str | None = None,
    limit: int = RATE_LIMIT_REQUESTS,
    window: int = RATE_LIMIT_WINDOW,
):
    """Check rate limit for request"""
    # In development, bypass rate limiting to avoid blocking local testing
    if DEBUG:
        return
    key = get_rate_limit_key(request, user_id)

    if not rate_limiter.is_allowed(key, limit, window):
        reset_time = rate_limiter.get_reset_time(key, window)
        retry_after = int(reset_time - time.time()) if reset_time else window

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Window": str(window),
                "X-RateLimit-Reset": str(int(reset_time))
                if reset_time
                else str(int(time.time() + window)),
            },
        )


def rate_limit(limit: int = RATE_LIMIT_REQUESTS, window: int = RATE_LIMIT_WINDOW):
    """Decorator for rate limiting endpoints"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from args/kwargs
            request = None
            user_id = None

            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if not request:
                for value in kwargs.values():
                    if isinstance(value, Request):
                        request = value
                        break

            if request:
                await check_rate_limit(request, user_id, limit, window)

            return await func(*args, **kwargs)

        return wrapper

    return decorator


# Specific rate limits for different endpoints
AI_RATE_LIMIT = settings.ai_requests_per_hour  # AI operations per hour (configurable)
AI_RATE_WINDOW = 3600

UPLOAD_RATE_LIMIT = 20  # File uploads per hour
UPLOAD_RATE_WINDOW = 3600

AUTH_RATE_LIMIT = 5  # Auth attempts per 15 minutes
AUTH_RATE_WINDOW = 900


async def check_ai_rate_limit(request: Request, user_id: str | None = None):
    """Rate limit for AI operations"""
    if DEBUG:
        return
    await check_rate_limit(request, user_id, AI_RATE_LIMIT, AI_RATE_WINDOW)


async def check_upload_rate_limit(request: Request, user_id: str | None = None):
    """Rate limit for file uploads"""
    await check_rate_limit(request, user_id, UPLOAD_RATE_LIMIT, UPLOAD_RATE_WINDOW)


async def check_auth_rate_limit(request: Request, user_id: str | None = None):
    """Rate limit for authentication attempts"""
    await check_rate_limit(request, user_id, AUTH_RATE_LIMIT, AUTH_RATE_WINDOW)
