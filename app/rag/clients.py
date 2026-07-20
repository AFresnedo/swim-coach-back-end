import anthropic
from anthropic.types import Message
from voyageai.client import Client as VoyageClient

from app.config import settings

anthropic_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
voyage_client = VoyageClient(api_key=settings.voyage_api_key)


def extract_response_text(response: Message, *, source: str) -> str:
    for block in response.content:
        if block.type == "text":
            return block.text
    raise RuntimeError(f"{source} response had no text block (stop_reason={response.stop_reason!r})")
