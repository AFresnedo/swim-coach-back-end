from pydantic_settings import BaseSettings, SettingsConfigDict


class RedisSettings(BaseSettings):
    """Backing store for app/rate_limit.py's counters."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # `limits`' own in-process "memory://" scheme is the test-only substitute,
    # mirroring sqlite's role for database_url. Real local dev and production both
    # set this to point at an actual Redis instance so counters are bounded and
    # shared across workers/instances instead of living in the API's own heap.
    redis_url: str = "memory://"
