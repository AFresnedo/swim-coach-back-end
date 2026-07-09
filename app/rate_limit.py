import time

from fastapi import HTTPException, Request, status
from limits import parse
from limits.storage import MemoryStorage, storage_from_string
from limits.strategies import FixedWindowRateLimiter

from app.config import settings

_storage = storage_from_string(settings.redis_url) if settings.redis_url else MemoryStorage()
_limiter = FixedWindowRateLimiter(_storage)

_TOO_MANY_REQUESTS_DETAIL = "Too many requests. Try again later."


def get_remote_address(request: Request) -> str:
    if not request.client or not request.client.host:
        return "127.0.0.1"
    return request.client.host


def enforce_rate_limit(limit_string: str, key: str) -> None:
    """Consume one hit against the given rate limit for the given key, raising 429
    if it's exceeded. Every rate limit in this app goes through this single,
    explicit helper - called directly in a route body with whatever key makes
    sense there (client IP, an email from the parsed request body, etc.) - rather
    than a decorator, since a prior decorator-based approach (slowapi) required
    reflection-based `request`/`response` parameters with no visible purpose in
    the route body, an easy-to-miss opt-in flag for header injection, and had no
    clean way to key a limit off a value only available after the request body is
    parsed. One uniform, explicit call site avoids all of that.
    """
    item = parse(limit_string)
    if not _limiter.hit(item, key):
        stats = _limiter.get_window_stats(item, key)
        retry_after = max(0, int(stats.reset_time - time.time()))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=_TOO_MANY_REQUESTS_DETAIL,
            headers={"Retry-After": str(retry_after)},
        )


def check_storage() -> None:
    """Startup check: verifies the rate-limit backing store (Redis when REDIS_URL is
    set, in-process memory otherwise) is reachable, so a bad REDIS_URL fails loudly
    at process boot instead of surfacing as a 500 on the first rate-limited request."""
    if not _storage.check():
        raise RuntimeError("Rate limit storage is not reachable")


def reset_rate_limits() -> None:
    """Test-only: clear all rate-limit state. The storage is a process-wide
    in-memory singleton, not reset between test cases automatically."""
    _storage.reset()
