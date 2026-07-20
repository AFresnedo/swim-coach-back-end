import time

from fastapi import HTTPException, Request, status
from limits import parse
from limits.errors import StorageError
from limits.storage import storage_from_string
from limits.strategies import FixedWindowRateLimiter

from app.config import settings

# wrap_exceptions=True makes every backend (Redis, memory, or whatever this becomes)
# raise the same limits.errors.StorageError on failure, so enforce_rate_limit() below
# can fail closed without needing to know which backend-specific exception to catch.
_storage = storage_from_string(settings.redis_url, wrap_exceptions=True)
_limiter = FixedWindowRateLimiter(_storage)

_TOO_MANY_REQUESTS_DETAIL = "Too many requests. Try again later."
_STORAGE_UNAVAILABLE_DETAIL = "Service temporarily unavailable. Try again shortly."


def get_remote_address(request: Request) -> str:
    if not request.client or not request.client.host:
        return "127.0.0.1"
    return request.client.host


def enforce_rate_limit(*, limit_string: str, key: str) -> None:
    """Consume one hit against the given rate limit for the given key, raising 429
    if it's exceeded. Every rate limit in this app goes through this single,
    explicit helper - called directly in a route body with whatever key makes
    sense there (client IP, an email from the parsed request body, etc.) - rather
    than a decorator, since a prior decorator-based approach (slowapi) required
    reflection-based `request`/`response` parameters with no visible purpose in
    the route body, an easy-to-miss opt-in flag for header injection, and had no
    clean way to key a limit off a value only available after the request body is
    parsed. One uniform, explicit call site avoids all of that.

    Fails closed: if the backing store itself is unreachable (e.g. Redis down),
    that's raised as a 503 rather than silently letting the request through
    unlimited - an outage shouldn't turn into an open door for brute-forcing
    login/register.
    """
    item = parse(limit_string)
    try:
        if not _limiter.hit(item, key):
            stats = _limiter.get_window_stats(item, key)
            retry_after = max(0, int(stats.reset_time - time.time()))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=_TOO_MANY_REQUESTS_DETAIL,
                headers={"Retry-After": str(retry_after)},
            )
    except StorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=_STORAGE_UNAVAILABLE_DETAIL,
        ) from exc


def check_storage() -> None:
    """Startup check: verifies the rate-limit backing store (Redis when REDIS_URL is
    set, in-process memory otherwise) is reachable, so a bad REDIS_URL fails loudly
    at process boot instead of surfacing as a 500 on the first rate-limited request."""
    if not _storage.check():
        raise RuntimeError("Rate limit storage is not reachable")


def reset_rate_limits() -> None:
    """Test-only: clear all rate-limit state. The storage is a process-wide singleton
    (in-memory in tests, potentially a shared Redis instance elsewhere), not reset
    between test cases automatically."""
    _storage.reset()
