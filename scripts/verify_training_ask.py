"""Ad-hoc end-to-end check for the /training/ask pipeline (see the "Hybrid RAG
training-coach endpoint" Trello card): calls ask_training() directly against a
real Postgres DB, real Anthropic, and real Voyage AI - no mocks - so the full
retrieval -> miss -> web-fallback -> ingestion path can be eyeballed the same
way scripts/spike_citations_ingestion_direct.py eyeballed raw Anthropic API
behavior.

Requires a real, already-migrated DATABASE_URL (see .env) plus
ANTHROPIC_API_KEY and VOYAGE_API_KEY set - this makes real, billed API calls.

    uv run python -m scripts.verify_training_ask "<swim training question>"

Prints the returned answer/sources/answered_from_knowledge_base, plus
whatever SwimKnowledge rows now exist for the returned sources, so an
ingestion (if any) is visible without a separate DB query. Also reports each
Anthropic turn's stop_reason during the web-fallback call, so it's visible
from the outside whether app/rag/web_fallback.py's tool-use continuation
(see _continue_after_tool_use) actually fired on this run, without adding any
logging to that production code itself - the proxy classes below only wrap
anthropic_client.messages.stream/create for the duration of this script's call.

Also seeds a Profile and an active Goal for the verify user, then checks
whether the exact swimmer-context string app/rag/swimmer_context.py builds
from them actually shows up in the system prompt(s) the API was sent - a
deterministic pass/fail on the personalization wiring, not just a vibe check
on whether the returned answer reads as personalized.
"""

import sys
from typing import Any
from unittest.mock import patch

from sqlalchemy import func, select

from app.database import SessionLocal, insert_skip_on_conflict
from app.goal.model import Goal
from app.profile.model import Profile
from app.rag.clients import anthropic_client
from app.rag.models import SwimKnowledge
from app.rag.swimmer_context import SwimmerContext, build_swimmer_context
from app.rag.training import ask_training
from app.security import hash_password
from app.user.model import User


class _RecordingMessageStream:
    """Proxies a real MessageStream so get_final_message()'s stop_reason gets
    appended to `log`, then delegates everything else untouched."""

    def __init__(self, real_message_stream: Any, log: list[str]) -> None:
        self._real_message_stream = real_message_stream
        self._log = log

    def get_final_message(self) -> Any:
        message = self._real_message_stream.get_final_message()
        self._log.append(message.stop_reason)
        return message

    def __getattr__(self, name: str) -> Any:
        return getattr(self._real_message_stream, name)


class _RecordingStreamManager:
    """Proxies the context manager anthropic_client.messages.stream(...)
    returns, handing out a _RecordingMessageStream from __enter__."""

    def __init__(self, real_manager: Any, log: list[str]) -> None:
        self._real_manager = real_manager
        self._log = log

    def __enter__(self) -> _RecordingMessageStream:
        return _RecordingMessageStream(self._real_manager.__enter__(), self._log)

    def __exit__(self, *exc_info: object) -> Any:
        return self._real_manager.__exit__(*exc_info)


_VERIFY_USER_EMAIL = "verify-training-ask@local.test"
_DEFAULT_QUESTION = "What's a good technique drill for improving my catch in freestyle?"

# Deliberately distinctive - a real personalized answer has a decent shot at
# referencing a 12-year-old's breaststroke goal explicitly, unlike a generic
# freestyle-catch question with no swimmer context at all.
_VERIFY_PROFILE = {"age": 12, "height_cm": 150.0, "weight_kg": 40.0, "sex": "female", "unit_preference": "metric"}
_VERIFY_GOAL_TEXT = "Break 1:40 in the 100 breaststroke by the end of the season"


def _get_or_create_verify_user(db) -> User:
    user = insert_skip_on_conflict(
        db,
        User,
        values={
            "name": "Verify Script",
            "email": _VERIFY_USER_EMAIL,
            "hashed_password": hash_password("not-a-real-password"),
        },
        conflict_columns=["email"],
    )
    if user is None:
        user = db.query(User).filter(User.email == _VERIFY_USER_EMAIL).one()
    db.commit()
    return user


def _get_or_create_verify_profile(db, user_id: int) -> Profile:
    profile = insert_skip_on_conflict(
        db, Profile, values={"user_id": user_id, **_VERIFY_PROFILE}, conflict_columns=["user_id"]
    )
    if profile is None:
        profile = db.query(Profile).filter(Profile.user_id == user_id).one()
    db.commit()
    return profile


def _get_or_create_verify_goal(db, user_id: int) -> Goal:
    goal = db.query(Goal).filter(Goal.user_id == user_id, Goal.is_active.is_(True)).first()
    if goal is not None:
        return goal
    goal = Goal(user_id=user_id, text=_VERIFY_GOAL_TEXT, is_active=True)
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


def _knowledge_base_row_count(db) -> int:
    return db.scalar(select(func.count()).select_from(SwimKnowledge))


def main() -> None:
    question = sys.argv[1] if len(sys.argv) > 1 else _DEFAULT_QUESTION
    print(f"Question: {question}\n")

    original_stream = anthropic_client.messages.stream
    original_create = anthropic_client.messages.create
    stop_reasons: list[str] = []
    system_prompts: list[str] = []

    def _stream_with_logging(*args: object, **kwargs: object) -> _RecordingStreamManager:
        system_prompts.append(str(kwargs.get("system", "")))
        return _RecordingStreamManager(original_stream(*args, **kwargs), stop_reasons)

    def _create_with_logging(*args: object, **kwargs: object) -> Any:
        system_prompts.append(str(kwargs.get("system", "")))
        return original_create(*args, **kwargs)

    with SessionLocal() as db:
        user = _get_or_create_verify_user(db)
        profile = _get_or_create_verify_profile(db, user.id)
        goal = _get_or_create_verify_goal(db, user.id)
        expected_context = build_swimmer_context(SwimmerContext(profile=profile, goals=[goal]))

        print("Personalization input:")
        print(f"  profile: age={profile.age}, sex={profile.sex}")
        print(f"  active goal: {goal.text!r}")
        print(f"  expected swimmer context string: {expected_context!r}\n")

        before_count = _knowledge_base_row_count(db)

        with (
            patch.object(anthropic_client.messages, "stream", side_effect=_stream_with_logging),
            patch.object(anthropic_client.messages, "create", side_effect=_create_with_logging),
        ):
            result = ask_training(db, user_id=user.id, raw_question=question)

        after_count = _knowledge_base_row_count(db)
        ingested_rows = (
            db.query(SwimKnowledge).filter(SwimKnowledge.source_url.in_(result.sources)).all()
            if result.sources
            else []
        )

    print(f"answered_from_knowledge_base: {result.answered_from_knowledge_base}")
    print(f"sources: {result.sources}\n")
    print("answer:")
    print(result.answer)
    print(f"\nSwimKnowledge rows: {before_count} -> {after_count}")

    if ingested_rows:
        print(f"\n{len(ingested_rows)} chunk(s) now in SwimKnowledge for the returned sources:")
        for row in ingested_rows:
            print(f"  [{row.quality_flag}] {row.source_url}: {row.chunk_text[:120]!r}")

    if not stop_reasons:
        print("\nAnthropic web-fallback turns: 0 (answered from the knowledge base, web fallback not called)")
    else:
        print(f"\nAnthropic web-fallback turns: {len(stop_reasons)} (stop_reason per turn: {stop_reasons})")
        if len(stop_reasons) > 1:
            print("-> tool-use continuation fired (this is the path _continue_after_tool_use handles)")
        else:
            print("-> single turn, no continuation needed")

    # Only counts calls whose system prompt has a "Swimmer context:" section at
    # all (answer_from_knowledge / answer_with_web_fallback / sharpen_question)
    # - excludes e.g. app/rag/clean.py's cleaning call, which has no swimmer
    # context section to check and would otherwise just be noise here.
    swimmer_aware_prompts = [prompt for prompt in system_prompts if "Swimmer context:" in prompt]
    matches = [prompt for prompt in swimmer_aware_prompts if expected_context in prompt]
    print()
    if not swimmer_aware_prompts:
        print("Personalization check: FAIL - no call with a swimmer-context-aware system prompt was made at all.")
    elif matches:
        print(
            f"Personalization check: PASS - expected swimmer context string found in "
            f"{len(matches)}/{len(swimmer_aware_prompts)} swimmer-aware system prompt(s) sent."
        )
    else:
        print(
            f"Personalization check: FAIL - expected swimmer context string not found in any of the "
            f"{len(swimmer_aware_prompts)} swimmer-aware system prompt(s) sent."
        )
        print(f"  expected: {expected_context!r}")


if __name__ == "__main__":
    main()
