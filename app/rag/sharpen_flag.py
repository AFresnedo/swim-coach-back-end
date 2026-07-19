"""Runtime toggle for Step 3b's miss-rescue sharpening (see the "Hybrid RAG
training-coach endpoint" Trello card). Redis-only, no env var: a Redis key is
the single source of truth for whether sharpening runs, so it can be flipped
without a restart. Toggle with e.g. `redis-cli SET training:sharpen_enabled 1`.

Falls back to disabled whenever Redis can't answer - unset key, unreachable
server, or (in local dev/tests) REDIS_URL set to "memory://", the rate
limiter's own in-process scheme that isn't a real Redis URL at all. Unlike
app/rate_limit.py, which fails closed (503) when its storage is unreachable,
this flag fails to its default instead - a training-answer request shouldn't
error out over an unrelated feature toggle being unreadable.
"""

import redis

from app.config import settings

REDIS_KEY = "training:sharpen_enabled"
FALLBACK_ENABLED = False

try:
    _redis_client: redis.Redis | None = redis.Redis.from_url(
        settings.redis_url, socket_connect_timeout=1, socket_timeout=1, decode_responses=True
    )
except ValueError:
    _redis_client = None


def is_sharpen_enabled() -> bool:
    if _redis_client is None:
        return FALLBACK_ENABLED
    try:
        value = _redis_client.get(REDIS_KEY)
    except redis.RedisError:
        return FALLBACK_ENABLED
    return value == "1"
