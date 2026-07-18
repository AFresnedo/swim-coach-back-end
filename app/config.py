from typing import Literal

from limits import parse
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Just database_url, split out from Settings below so that anything which only
    needs to open a DB connection - app/database.py's engine, alembic/env.py - can
    construct this instead of the full Settings. Otherwise every required secret
    (secret_key, anthropic_api_key, ...) would have to be present just to run a
    migration or import app.database, even though migrations never touch them.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./swimcoach.db"


database_settings = DatabaseSettings()


class Settings(DatabaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Defaults to "development" so a plain local `uvicorn --reload` run needs no
    # setup. Deployed environments (see ../infra/docker-compose.yml) set
    # ENVIRONMENT=production explicitly. Also gates /docs, /redoc, and
    # /openapi.json (see app/main.py): those reflect the full, uncurated
    # schema, so they're never meant to be reachable in production. A future
    # public API's docs would be a separate, deliberately curated surface with
    # its own setting - not this flag repurposed.
    environment: Literal["development", "production"] = "development"

    secret_key: str
    access_token_expire_minutes: int = 60 * 24

    # `limits`' own in-process "memory://" scheme is the test-only substitute,
    # mirroring sqlite's role for database_url above. Real local dev and production both
    # set this to point at an actual Redis instance so counters are bounded and
    # shared across workers/instances instead of living in the API's own heap.
    redis_url: str = "memory://"

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

    # No default, same "fail now, not silently later" stance as secret_key above -
    # the hybrid RAG coach endpoint (see the "Hybrid RAG training-coach endpoint"
    # Trello card) can't run without these, so a missing key should surface at
    # process boot rather than as a 401 on the first request that needs it.
    anthropic_api_key: str
    voyage_api_key: str

    # Card step 3 specifies Sonnet 5 with an explicit config-swap escape hatch to
    # Haiku - not a free-form model string, so a typo'd model id fails at startup
    # (pydantic ValidationError) instead of a confusing 404 from the Anthropic API.
    coach_model: Literal["claude-sonnet-5", "claude-haiku-4-5"] = "claude-sonnet-5"

    # Card step 3: "if best match >= SIMILARITY_THRESHOLD (TBD)". Starting value,
    # not a tuned one - revisit once the endpoint is live and there's real
    # KB-hit/miss data to tune against.
    similarity_threshold: float = Field(default=0.75, ge=0.0, le=1.0)

    # Ingestion guardrail: caps how many web-search results get chunked/embedded/
    # stored per fallback trigger (card step 4 fetches "the top 1-2 results").
    max_web_ingestions_per_query: int = Field(default=2, ge=1)


# secret_key has no default (see above), so pyright statically sees a required
# constructor argument here - but pydantic-settings sources it from the SECRET_KEY
# env var / .env file at runtime, not from this call site. Missing/empty at runtime
# still fails loudly, just via a pydantic ValidationError instead of a type error.
settings = Settings()  # pyright: ignore[reportCallIssue]
