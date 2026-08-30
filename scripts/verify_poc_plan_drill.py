"""POC-only: ad-hoc end-to-end check for the new /training/plan and
/training/drill endpoints (real DB, real Anthropic, no mocks) - mirrors
scripts/verify_training_ask.py's approach. Reuses the same verify user that
script seeds (profile + active goal) so plan generation has something real to
personalize against.

    uv run python -m scripts.verify_poc_plan_drill
"""

from app.database import SessionLocal
from app.rag.drill import generate_drill
from app.rag.plan import generate_plan
from app.user.model import User

_VERIFY_USER_EMAIL = "verify-training-ask@local.test"


def main() -> None:
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == _VERIFY_USER_EMAIL).first()
        if user is None:
            raise SystemExit(
                f"No user {_VERIFY_USER_EMAIL!r} - run `uv run python -m scripts.verify_training_ask` first "
                "to seed it."
            )

        print("=== /training/plan ===")
        plan = generate_plan(db, user_id=user.id, weeks=2, sessions_per_week=3)
        print(f"summary: {plan.summary}")
        print(f"weeks returned: {len(plan.weeks)} (requested 2)")
        for week in plan.weeks:
            print(f"  week {week.week_number}: {len(week.sessions)} session(s) (requested 3)")

        print("\n=== /training/drill ===")
        drill = generate_drill(stroke="butterfly", focus="timing", skill_level="advanced")
        print(f"name: {drill.name}")
        print(f"steps: {len(drill.steps)}")
        print(f"set: {drill.set}")


if __name__ == "__main__":
    main()
