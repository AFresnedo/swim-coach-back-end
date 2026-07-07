from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./swimcoach.db"
    secret_key: str
    access_token_expire_minutes: int = 60 * 24


# secret_key has no default (see above), so pyright statically sees a required
# constructor argument here - but pydantic-settings sources it from the SECRET_KEY
# env var / .env file at runtime, not from this call site. Missing/empty at runtime
# still fails loudly, just via a pydantic ValidationError instead of a type error.
settings = Settings()  # pyright: ignore[reportCallIssue]
