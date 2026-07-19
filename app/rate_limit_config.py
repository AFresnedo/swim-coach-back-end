from limits import parse
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class RateLimitSettings(BaseSettings):
    """Rate limit thresholds consumed by app/rate_limit.py's enforce_rate_limit()."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

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
    # "fail now, not silently later" stance taken for secret_key.
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
