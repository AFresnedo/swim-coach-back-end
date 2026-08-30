"""Swimmer profile/goals context, shared by every RAG pipeline step that
personalizes a Claude call to the swimmer asking (see the "Hybrid RAG
training-coach endpoint" Trello card, step 6): app/rag/sharpen.py's question
rewrite, app/rag/answer.py's KB-hit answer, and app/rag/web_fallback.py's
web-fallback answer.
"""

from collections.abc import Sequence

from app.goal.model import Goal
from app.profile.model import Profile


def _demographics(profile: Profile | None) -> str:
    if profile is None:
        return ""
    if profile.sex == "prefer_not_to_say":
        return f"{profile.age}yo"
    return f"{profile.age}yo {profile.sex}"


def _goals_summary(goals: Sequence[Goal]) -> str:
    return ", ".join(goal.text for goal in goals)


def build_swimmer_context(profile: Profile | None, goals: Sequence[Goal]) -> str:
    segments = []
    demographics = _demographics(profile)
    if demographics:
        segments.append(demographics)
    goals_summary = _goals_summary(goals)
    if goals_summary:
        segments.append(f"active goals: {goals_summary}")
    return "; ".join(segments) if segments else "no profile or goals on file"
