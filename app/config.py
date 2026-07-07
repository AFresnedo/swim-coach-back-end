from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

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


# secret_key has no default (see above), so pyright statically sees a required
# constructor argument here - but pydantic-settings sources it from the SECRET_KEY
# env var / .env file at runtime, not from this call site. Missing/empty at runtime
# still fails loudly, just via a pydantic ValidationError instead of a type error.
settings = Settings()  # pyright: ignore[reportCallIssue]
