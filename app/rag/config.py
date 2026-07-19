from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RagSettings(BaseSettings):
    """Hybrid RAG training-coach settings, consumed by app/rag/clients.py and the
    coach endpoint (see the "Hybrid RAG training-coach endpoint" Trello card)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # No default, same "fail now, not silently later" stance as secret_key -
    # the coach endpoint can't run without these, so a missing key should surface
    # at process boot rather than as a 401 on the first request that needs it.
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

    # Step 3b's miss-rescue question rewrite. A separate knob from coach_model,
    # not the same setting reused - the rescue only pays for itself economically
    # if this stays on whichever model is cheapest, independent of what
    # coach_model is configured to answer with. Today's cheapest model happens
    # to be Haiku 4.5; that will change, which is exactly why this is a setting
    # instead of a hardcoded model id.
    sharpen_model: Literal["claude-haiku-4-5"] = "claude-haiku-4-5"
