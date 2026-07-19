from typing import Literal

from pydantic_settings import SettingsConfigDict

from app.auth_config import AuthSettings
from app.db_config import DatabaseSettings
from app.rag.config import RagSettings
from app.rate_limit_config import RateLimitSettings
from app.redis_config import RedisSettings


class Settings(DatabaseSettings, AuthSettings, RedisSettings, RateLimitSettings, RagSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Defaults to "development" so a plain local `uvicorn --reload` run needs no
    # setup. Deployed environments (see ../infra/docker-compose.yml) set
    # ENVIRONMENT=production explicitly. Also gates /docs, /redoc, and
    # /openapi.json (see app/main.py): those reflect the full, uncurated
    # schema, so they're never meant to be reachable in production. A future
    # public API's docs would be a separate, deliberately curated surface with
    # its own setting - not this flag repurposed.
    environment: Literal["development", "production"] = "development"


# secret_key has no default (see AuthSettings), so pyright statically sees a required
# constructor argument here - but pydantic-settings sources it from the SECRET_KEY
# env var / .env file at runtime, not from this call site. Missing/empty at runtime
# still fails loudly, just via a pydantic ValidationError instead of a type error.
settings = Settings()  # pyright: ignore[reportCallIssue]
