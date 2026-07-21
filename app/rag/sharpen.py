"""Step 3b of the hybrid RAG training-coach pipeline: on a KB miss, rewrite
the question with a cheap-model call grounded in swimmer profile + active
goals, so the re-embedded retry has a better shot at clearing the similarity
threshold (see the "Hybrid RAG training-coach endpoint" Trello card).
"""

from collections.abc import Sequence

from app.config import settings
from app.goal.model import Goal
from app.profile.model import Profile
from app.rag.clients import anthropic_client, extract_response_text

MAX_SHARPEN_TOKENS = 256

_SYSTEM_PROMPT = """Rewrite the swimmer's question into a specific, well-formed \
training question a knowledge base search could match against. Use the \
swimmer context below to resolve vague references (e.g. "my stroke", "get \
faster") into something concrete. Output only the rewritten question, nothing \
else.

Swimmer context:
{context}"""


def _demographics(profile: Profile | None) -> str:
    if profile is None:
        return ""
    if profile.sex == "prefer_not_to_say":
        return f"{profile.age}yo"
    return f"{profile.age}yo {profile.sex}"


def _goals_summary(goals: Sequence[Goal]) -> str:
    return ", ".join(goal.text for goal in goals)


def _build_swimmer_context(profile: Profile | None, goals: Sequence[Goal]) -> str:
    segments = []
    demographics = _demographics(profile)
    if demographics:
        segments.append(demographics)
    goals_summary = _goals_summary(goals)
    if goals_summary:
        segments.append(f"active goals: {goals_summary}")
    return "; ".join(segments) if segments else "no profile or goals on file"


def sharpen_question(question: str, *, profile: Profile | None, goals: Sequence[Goal]) -> str:
    system = _SYSTEM_PROMPT.format(context=_build_swimmer_context(profile, goals))
    response = anthropic_client.messages.create(
        model=settings.sharpen_model,
        max_tokens=MAX_SHARPEN_TOKENS,
        system=system,
        messages=[{"role": "user", "content": question}],
    )
    return extract_response_text(response, source="Claude").strip()
