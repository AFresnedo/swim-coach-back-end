"""Ingestion-time content cleaning for card step 4 (see the "Hybrid RAG
training-coach endpoint" Trello card's ingestion guardrails): a fetched
page's raw text - already flattened to plain text/markdown by web_fetch, with
no HTML structure left to tell "article" from "nav menu" or "comment
reply" - gets a cheap-model pass to strip that noise before it's chunked and
embedded, so SwimKnowledge stores the article, not the page's chrome.
"""

from app.config import settings
from app.rag.clients import anthropic_client, extract_response_text

MAX_CLEAN_TOKENS = 8000

_SYSTEM_PROMPT = """The following is the raw text of a fetched web page, already \
converted to plain text. Remove site navigation, menus, ads, subscription prompts, \
related-post widgets, footers, and reader comments. Keep everything else exactly as \
written - do not summarize, paraphrase, or add commentary. Output only the remaining \
article text."""


def clean_fetched_text(raw_text: str) -> str:
    response = anthropic_client.messages.create(
        model=settings.clean_model,
        max_tokens=MAX_CLEAN_TOKENS,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": raw_text}],
    )
    return extract_response_text(response, source="Claude").strip()
