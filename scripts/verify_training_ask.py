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
anthropic_client.messages.stream for the duration of this script's call.
"""

import sys
from typing import Any
from unittest.mock import patch

from sqlalchemy import func, select

from app.database import SessionLocal, insert_skip_on_conflict
from app.rag.clients import anthropic_client
from app.rag.models import SwimKnowledge
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


def _knowledge_base_row_count(db) -> int:
    return db.scalar(select(func.count()).select_from(SwimKnowledge))


def main() -> None:
    question = sys.argv[1] if len(sys.argv) > 1 else _DEFAULT_QUESTION
    print(f"Question: {question}\n")

    original_stream = anthropic_client.messages.stream
    stop_reasons: list[str] = []

    def _stream_with_logging(*args: object, **kwargs: object) -> _RecordingStreamManager:
        return _RecordingStreamManager(original_stream(*args, **kwargs), stop_reasons)

    with SessionLocal() as db:
        user = _get_or_create_verify_user(db)
        before_count = _knowledge_base_row_count(db)

        with patch.object(anthropic_client.messages, "stream", side_effect=_stream_with_logging):
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


if __name__ == "__main__":
    main()
