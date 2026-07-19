from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthSettings(BaseSettings):
    """JWT signing/expiry, consumed by app/security.py."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # No default, "fail now, not silently later" - a blank/default signing key
    # would silently make every issued token forgeable.
    secret_key: str
    access_token_expire_minutes: int = 60 * 24
