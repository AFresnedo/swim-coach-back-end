"""Step 4 of the hybrid RAG training-coach pipeline: once retrieval (and the
optional Step 3b rescue) both miss, search and fetch from a vetted domain
allowlist and answer grounded in what was found, surfacing ingestion
candidates for the fetched pages (see the "Hybrid RAG training-coach
endpoint" Trello card).
"""

import base64
from dataclasses import dataclass
from typing import Any

from anthropic.types import (
    MessageParam,
    ToolParam,
    ToolResultBlockParam,
    ToolUnionParam,
    WebFetchTool20260209Param,
    WebSearchTool20260209Param,
)

from app.config import settings
from app.enums import STROKES
from app.rag.clients import anthropic_client
from app.rag.models import ALLOWED_WEB_DOMAINS, QUALITY_FLAGS, SKILL_LEVELS, TOPIC_CATEGORIES
from app.rag.pdf_extract import extract_pdf_text

# Matches the value the confirming spike (see the card's step 4) ran
# successfully with - a starting value, not a tuned one.
MAX_FALLBACK_TOKENS = 8000

# Not a card-mandated guardrail like web_fetch's max_uses below, so it's a
# plain constant rather than a RagSettings field - just a cap on how many
# searches one fallback call may run before it must fetch and answer.
MAX_WEB_SEARCHES = 3

_SUBMIT_CANDIDATES_TOOL_NAME = "submit_ingestion_candidates"

# Fetching must be required, not left optional - an optional web_fetch lets
# the model reasonably answer from search snippets alone and skip ingestion
# entirely, defeating the KB's self-improvement loop.
_SYSTEM_PROMPT = """You are a swim coach assistant answering a training question using \
live web search, restricted to a vetted set of swim-coaching sources. Search first, \
then use web_fetch to retrieve the full content of at least one of the most relevant \
pages you found - never answer from search snippets alone, always fetch at least one \
page for the full detail. Answer the swimmer's question grounded in what you fetched. \
After answering, call submit_ingestion_candidates once, listing every page you fetched \
that's worth keeping in a knowledge base for future questions."""


def _nullable_enum(values: tuple[str, ...]) -> dict[str, Any]:
    """JSON Schema for an optional classification value: one of `values`, or
    null when nothing in the fixed set applies to this candidate."""
    return {"anyOf": [{"type": "string", "enum": list(values)}, {"type": "null"}]}


_SUBMIT_CANDIDATES_TOOL: ToolParam = {
    "name": _SUBMIT_CANDIDATES_TOOL_NAME,
    "description": (
        "Submit knowledge-base ingestion candidates for pages you fetched while "
        "answering. Call this once you've finished searching and fetching, alongside "
        "your normal answer text. One entry per fetched page worth keeping."
    ),
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "candidates": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "source_url": {"type": "string"},
                        "quality_score": {"type": "number"},
                        "quality_flag": {"type": "string", "enum": list(QUALITY_FLAGS)},
                        "quality_reason": {"type": "string"},
                        "stroke_type": _nullable_enum(STROKES),
                        "topic_category": _nullable_enum(TOPIC_CATEGORIES),
                        "skill_level": _nullable_enum(SKILL_LEVELS),
                    },
                    "required": [
                        "source_url",
                        "quality_score",
                        "quality_flag",
                        "quality_reason",
                        "stroke_type",
                        "topic_category",
                        "skill_level",
                    ],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["candidates"],
        "additionalProperties": False,
    },
}


def _tools() -> list[ToolUnionParam]:
    # allowed_callers: ["direct"] is required on both server tools, not
    # incidental: left unset, web_search_20260209/web_fetch_20260209 default
    # to routing through an internal code-execution caller, which silently
    # drops citations (every text block comes back with citations: null even
    # when content is clearly pulled from a fetched page) and breaks
    # continuing the turn past this module's submit_ingestion_candidates
    # tool_use (the API rejects it with a 400 needing a container_id that
    # code-execution-routed calls never actually returned).
    web_search_tool: WebSearchTool20260209Param = {
        "type": "web_search_20260209",
        "name": "web_search",
        "max_uses": MAX_WEB_SEARCHES,
        "allowed_domains": list(ALLOWED_WEB_DOMAINS),
        "allowed_callers": ["direct"],
    }
    web_fetch_tool: WebFetchTool20260209Param = {
        "type": "web_fetch_20260209",
        "name": "web_fetch",
        # Doubles as the ingestion guardrails checklist's "max N
        # ingestions per query" cap: every SwimKnowledge write this step
        # can produce traces back to a page that was fetched here.
        "max_uses": settings.max_web_ingestions_per_query,
        "allowed_domains": list(ALLOWED_WEB_DOMAINS),
        "citations": {"enabled": True},
        "allowed_callers": ["direct"],
    }
    return [web_search_tool, web_fetch_tool, _SUBMIT_CANDIDATES_TOOL]


@dataclass(frozen=True)
class FetchedPage:
    source_url: str
    raw_text: str
    quality_score: float | None
    quality_flag: str
    quality_reason: str | None
    stroke_type: str | None
    topic_category: str | None
    skill_level: str | None


@dataclass(frozen=True)
class WebFallbackResult:
    answer: str
    sources: list[str]
    fetched_pages: list[FetchedPage]


def _is_fetch(block: Any) -> bool:
    return block.type == "web_fetch_tool_result" and block.content.type == "web_fetch_result"


def _is_text_fetch(block: Any) -> bool:
    return _is_fetch(block) and block.content.content.source.type == "text"


def _is_pdf_fetch(block: Any) -> bool:
    return (
        _is_fetch(block)
        and block.content.content.source.type == "base64"
        and block.content.content.source.media_type == "application/pdf"
    )


def _pdf_fetched_text_by_url(content: list[Any]) -> dict[str, str]:
    """Only reached when settings.pdf_extraction_enabled is True (see
    _fetched_text_by_url) - decodes each fetched PDF's base64 source and runs
    it through pdfminer.six. A PDF extract_pdf_text can't get text out of
    (corrupt file, unsupported encoding) is left out of the result, dropping
    its candidate exactly like a hallucinated URL would be."""
    pages = {}
    for block in content:
        if not _is_pdf_fetch(block):
            continue
        pdf_bytes = base64.b64decode(block.content.content.source.data)
        text = extract_pdf_text(pdf_bytes)
        if text is not None:
            pages[block.content.url] = text
    return pages


def _fetched_text_by_url(content: list[Any]) -> dict[str, str]:
    fetched = {block.content.url: block.content.content.source.data for block in content if _is_text_fetch(block)}
    if settings.pdf_extraction_enabled:
        fetched.update(_pdf_fetched_text_by_url(content))
    return fetched


def _fetched_urls_in_order(content: list[Any]) -> list[str]:
    """CitationCharLocation.document_index refers to a position in this same
    order - the order the API returned fetched documents in, which is also
    the only order citations can reference since citations are enabled only
    on web_fetch (not web_search) in this call. Every web_fetch result counts
    as a document slot for this indexing, text and PDF alike (a PDF page is
    just cited with a different location type, page_location, rather than
    char_location) - filtering this list down to text-only fetches would
    shift every index after a PDF fetch onto the wrong URL."""
    return [block.content.url for block in content if _is_fetch(block)]


def _cited_url(citation: Any, document_urls: list[str]) -> str | None:
    # Two citation types can appear here: char_location points into a fetched
    # document by document_index, resolved against document_urls (the only
    # order that index can mean, since citations are enabled only on
    # web_fetch in this call). web_search_result_location already carries its
    # own url - the system prompt tells the model to always fetch and answer
    # from that, not from search snippets, but nothing at the API level stops
    # it from citing a snippet directly anyway, so both are handled.
    if citation.type == "char_location" and citation.document_index < len(document_urls):
        return document_urls[citation.document_index]
    if citation.type == "web_search_result_location":
        return citation.url
    return None


def _extract_answer_and_sources(content: list[Any]) -> tuple[str, list[str]]:
    """The API splits one continuous answer into multiple text blocks at
    citation boundaries - concatenating every text block's .text in order
    reproduces exactly what an uncited response would have read, so no
    separator belongs between them."""
    document_urls = _fetched_urls_in_order(content)
    answer_parts = []
    source_urls: dict[str, None] = {}
    for block in content:
        if block.type != "text":
            continue
        answer_parts.append(block.text)
        for citation in block.citations or []:
            url = _cited_url(citation, document_urls)
            if url is not None:
                source_urls[url] = None
    return "".join(answer_parts), list(source_urls)


def _extract_fetched_pages(content: list[Any]) -> list[FetchedPage]:
    """Pairs each ingestion candidate the model reported with the actual text
    it fetched. A candidate whose source_url has no matching text fetch is
    dropped silently - there's nothing to chunk or embed for it. That happens
    for a hallucinated URL, for a PDF fetch when pdf_extraction_enabled is
    off, or for a PDF pdfminer.six couldn't extract text from."""
    fetched_text = _fetched_text_by_url(content)
    pages = []
    for block in content:
        if block.type != "tool_use" or block.name != _SUBMIT_CANDIDATES_TOOL_NAME:
            continue
        for candidate in block.input["candidates"]:
            raw_text = fetched_text.get(candidate["source_url"])
            if raw_text is None:
                continue
            pages.append(
                FetchedPage(
                    source_url=candidate["source_url"],
                    raw_text=raw_text,
                    quality_score=candidate["quality_score"],
                    quality_flag=candidate["quality_flag"],
                    quality_reason=candidate["quality_reason"],
                    stroke_type=candidate["stroke_type"],
                    topic_category=candidate["topic_category"],
                    skill_level=candidate["skill_level"],
                )
            )
    return pages


def _continue_after_tool_use(response: Any, messages: list[MessageParam], tools: list[ToolUnionParam]) -> Any:
    """Confirmed necessary by scripts/spike_citations_ingestion_direct.py: the
    model doesn't reliably write its swimmer-facing answer before calling
    submit_ingestion_candidates, even though the system prompt asks for that
    order. stop_reason "tool_use" means the API has paused the turn waiting
    on a tool_result for that call - the real answer, citations included,
    isn't necessarily in `response` yet and only shows up once we send a
    tool_result back and continue."""
    tool_results: list[ToolResultBlockParam] = [
        {"type": "tool_result", "tool_use_id": block.id, "content": "Candidates recorded."}
        for block in response.content
        if block.type == "tool_use"
    ]
    messages.append({"role": "assistant", "content": response.content})
    messages.append({"role": "user", "content": tool_results})

    # Not expected to ever be set under allowed_callers: direct (that's what
    # sidesteps the code-execution container in the first place), but the
    # confirming spike checked for it defensively, so this does too.
    continuation_kwargs: dict[str, Any] = {}
    if response.container is not None:
        continuation_kwargs["container"] = response.container.id

    with anthropic_client.messages.stream(
        model=settings.coach_model,
        max_tokens=MAX_FALLBACK_TOKENS,
        system=_SYSTEM_PROMPT,
        tools=tools,
        messages=messages,
        **continuation_kwargs,
    ) as stream:
        return stream.get_final_message()


def answer_with_web_fallback(question: str) -> WebFallbackResult:
    """Card step 4: search + fetch from ALLOWED_WEB_DOMAINS and answer
    grounded in what was found. The caller only takes this path once
    retrieval (and the optional Step 3b rescue) both miss."""
    messages: list[MessageParam] = [{"role": "user", "content": question}]
    tools = _tools()

    with anthropic_client.messages.stream(
        model=settings.coach_model,
        max_tokens=MAX_FALLBACK_TOKENS,
        system=_SYSTEM_PROMPT,
        tools=tools,
        messages=messages,
    ) as stream:
        response = stream.get_final_message()

    full_content = list(response.content)
    if response.stop_reason == "tool_use":
        continuation = _continue_after_tool_use(response, messages, tools)
        full_content += continuation.content

    answer, sources = _extract_answer_and_sources(full_content)
    fetched_pages = _extract_fetched_pages(full_content)
    return WebFallbackResult(answer=answer, sources=sources, fetched_pages=fetched_pages)
