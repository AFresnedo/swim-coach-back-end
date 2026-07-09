from typing import Literal

from limits import parse
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Defaults to "development" so a plain local `uvicorn --reload` run needs no
    # setup. Deployed environments (see ../infra/docker-compose.yml) set
    # ENVIRONMENT=production explicitly. Also gates /docs, /redoc, and
    # /openapi.json (see app/main.py): those reflect the full, uncurated
    # schema, so they're never meant to be reachable in production. A future
    # public API's docs would be a separate, deliberately curated surface with
    # its own setting - not this flag repurposed.
    environment: Literal["development", "production"] = "development"

    database_url: str = "sqlite:///./swimcoach.db"
    secret_key: str
    access_token_expire_minutes: int = 60 * 24

    # Rate limits, expressed in the `limits` library's string syntax (e.g. "5/5minutes",
    # "20/hour") consumed directly by app.rate_limit.enforce_rate_limit(). Kept
    # configurable via env vars rather than hardcoded so they can be tuned in production
    # without a code change/redeploy.
    login_rate_limit_per_email: str = "5/5minutes"
    login_rate_limit_per_ip: str = "20/5minutes"
    register_rate_limit_per_ip: str = "5/hour"
    stats_rate_limit_per_ip: str = "30/minute"

    # enforce_rate_limit() re-parses these strings on every single request rather
    # than once at startup, so a typo here would otherwise go unnoticed until the
    # first real login/register attempt hits an unhandled ValueError. Validating
    # here instead makes a bad value fail loudly at process startup, the same
    # "fail now, not silently later" stance taken for secret_key above.
    @field_validator(
        "login_rate_limit_per_email",
        "login_rate_limit_per_ip",
        "register_rate_limit_per_ip",
        "stats_rate_limit_per_ip",
    )
    @classmethod
    def _validate_rate_limit_string(cls, value: str) -> str:
        parse(value)
        return value


# secret_key has no default (see above), so pyright statically sees a required
# constructor argument here - but pydantic-settings sources it from the SECRET_KEY
# env var / .env file at runtime, not from this call site. Missing/empty at runtime
# still fails loudly, just via a pydantic ValidationError instead of a type error.
settings = Settings()  # pyright: ignore[reportCallIssue]
