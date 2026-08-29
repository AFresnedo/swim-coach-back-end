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
ingestion (if any) is visible without a separate DB query.
"""

import sys

from sqlalchemy import func, select

from app.database import SessionLocal, insert_skip_on_conflict
from app.rag.models import SwimKnowledge
from app.rag.training import ask_training
from app.security import hash_password
from app.user.model import User

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

    with SessionLocal() as db:
        user = _get_or_create_verify_user(db)
        before_count = _knowledge_base_row_count(db)

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


if __name__ == "__main__":
    main()
