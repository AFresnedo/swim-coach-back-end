import anthropic
from voyageai.client import Client as VoyageClient

from app.config import settings

anthropic_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
voyage_client = VoyageClient(api_key=settings.voyage_api_key)
