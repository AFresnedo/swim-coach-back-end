from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Just database_url, kept in its own module so that anything which only
    needs to open a DB connection - app/database.py's engine, alembic/env.py - can
    import this without pulling in app/config.py's Settings, which requires
    secrets (secret_key, anthropic_api_key, ...) that migrations never touch.
    Importing from the same module as Settings wouldn't work: Python executes
    a module fully on first import, so even a name-only import of
    DatabaseSettings would still run Settings() and demand those secrets.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./swimcoach.db"


database_settings = DatabaseSettings()
