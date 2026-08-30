"""Step 3b of the hybrid RAG training-coach pipeline: on a KB miss, rewrite
the question with a cheap-model call grounded in swimmer profile + active
goals, so the re-embedded retry has a better shot at clearing the similarity
threshold (see the "Hybrid RAG training-coach endpoint" Trello card).
"""

from app.config import settings
from app.rag.clients import anthropic_client, extract_response_text
from app.rag.swimmer_context import SwimmerContext, build_swimmer_context

MAX_SHARPEN_TOKENS = 256

_SYSTEM_PROMPT = """Rewrite the swimmer's question into a specific, well-formed \
training question a knowledge base search could match against. Use the \
swimmer context below to resolve vague references (e.g. "my stroke", "get \
faster") into something concrete. Output only the rewritten question, nothing \
else.

Swimmer context:
{context}"""


def sharpen_question(question: str, *, swimmer: SwimmerContext) -> str:
    system = _SYSTEM_PROMPT.format(context=build_swimmer_context(swimmer))
    response = anthropic_client.messages.create(
        model=settings.sharpen_model,
        max_tokens=MAX_SHARPEN_TOKENS,
        system=system,
        messages=[{"role": "user", "content": question}],
    )
    return extract_response_text(response, source="Claude").strip()
