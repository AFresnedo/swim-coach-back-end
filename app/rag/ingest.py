"""Ingestion half of card step 4: chunk, embed, and write vetted fetched pages
into SwimKnowledge, applying the guardrails that govern this step (see the
"Hybrid RAG training-coach endpoint" Trello card's ingestion guardrails
checklist).

Domain filtering and the max-N-ingestions-per-query cap are both already
enforced upstream, by the tool definitions in app/rag/web_fallback.py
(allowed_domains, web_fetch's max_uses) - not repeated here. Periodic pruning
of stale/low-value chunks is a separate, not-yet-scheduled job (the card
leaves its schedule TBD), so it isn't part of this module either.
"""

from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy.orm import Session

from app.rag.embeddings import embed_documents
from app.rag.models import SwimKnowledge
from app.rag.web_fallback import FetchedPage

# Character-based, not token-based: good enough for a target chunk size and
# avoids adding a tokenizer dependency just for chunking. Starting values,
# not tuned - small enough to keep each embedded chunk topically focused for
# cosine search, not so small that routine coaching explanations get split
# mid-thought.
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150

_splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)


def _dedup_by_source_url(pages: list[FetchedPage]) -> list[FetchedPage]:
    seen: set[str] = set()
    unique = []
    for page in pages:
        if page.source_url in seen:
            continue
        seen.add(page.source_url)
        unique.append(page)
    return unique


def _already_ingested(db: Session, source_url: str) -> bool:
    return db.query(SwimKnowledge.id).filter(SwimKnowledge.source_url == source_url).first() is not None


def ingest_fetched_pages(db: Session, *, source_query: str, pages: list[FetchedPage]) -> list[SwimKnowledge]:
    """Chunk, embed, and persist each accepted page in `pages`.

    Two guardrails from the card's ingestion checklist are enforced here (the
    rest live upstream in web_fallback.py's tool definitions, per this
    module's docstring): a page is skipped if its quality_flag isn't "pass"
    (the LLM-assessed signal, layered on top of the deterministic guardrails
    rather than replacing them) or if its source_url is already present in
    SwimKnowledge (dedup).
    """
    accepted = [
        page
        for page in _dedup_by_source_url(pages)
        if page.quality_flag == "pass" and not _already_ingested(db, page.source_url)
    ]
    if not accepted:
        return []

    chunk_texts: list[str] = []
    chunk_owners: list[FetchedPage] = []
    for page in accepted:
        for chunk_text in _splitter.split_text(page.raw_text):
            chunk_texts.append(chunk_text)
            chunk_owners.append(page)

    embeddings = embed_documents(chunk_texts)

    rows = [
        SwimKnowledge(
            chunk_text=chunk_text,
            embedding=embedding,
            source_url=page.source_url,
            source_query=source_query,
            ingestion_reason="fallback_web_search",
            quality_score=page.quality_score,
            quality_flag=page.quality_flag,
            quality_reason=page.quality_reason,
            stroke_type=page.stroke_type,
            topic_category=page.topic_category,
            skill_level=page.skill_level,
        )
        for chunk_text, embedding, page in zip(chunk_texts, embeddings, chunk_owners, strict=True)
    ]
    db.add_all(rows)
    db.commit()
    return rows
