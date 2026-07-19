from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class DocsUrls:
    docs_url: str | None
    redoc_url: str | None
    openapi_url: str | None


def docs_urls(environment: Literal["development", "production"]) -> DocsUrls:
    # The full, uncurated OpenAPI schema is never meant to be reachable in
    # production (see Settings.environment) - a future public API's docs would
    # be a separate, deliberately curated surface with its own setting, not
    # this flag repurposed.
    enabled = environment != "production"
    return DocsUrls(
        docs_url="/docs" if enabled else None,
        redoc_url="/redoc" if enabled else None,
        openapi_url="/openapi.json" if enabled else None,
    )
