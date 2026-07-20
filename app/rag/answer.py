"""Step 3 of the hybrid RAG training-coach pipeline: answer a training
question from retrieved SwimKnowledge context, in a single Claude call with
no tools (see the "Hybrid RAG training-coach endpoint" Trello card).
"""

from app.config import settings
from app.rag.clients import anthropic_client, extract_response_text
from app.rag.retrieval import RetrievedChunk

_SYSTEM_PROMPT_TEMPLATE = """You are a swim coach assistant. Answer the swimmer's \
question using only the knowledge base excerpts provided below - do not draw on \
general knowledge. If the excerpts don't fully answer the question, say so \
explicitly rather than filling the gap yourself.

Knowledge base excerpts:
{context}"""

# Enough for a focused coaching answer without inviting the model to pad a
# short, grounded Q&A into an essay.
MAX_ANSWER_TOKENS = 1024


def _build_context(chunks: list[RetrievedChunk]) -> str:
    return "\n\n".join(f"Source: {result.chunk.source_url}\n{result.chunk.chunk_text}" for result in chunks)


def answer_from_knowledge(question: str, chunks: list[RetrievedChunk]) -> str:
    """Answer `question` grounded in `chunks` (the KB hit path - card step 3).
    `chunks` must be non-empty; the caller only takes this path once
    retrieval clears SIMILARITY_THRESHOLD."""
    system = _SYSTEM_PROMPT_TEMPLATE.format(context=_build_context(chunks))
    response = anthropic_client.messages.create(
        model=settings.coach_model,
        max_tokens=MAX_ANSWER_TOKENS,
        system=system,
        messages=[{"role": "user", "content": question}],
    )
    return extract_response_text(response, source="Claude")
