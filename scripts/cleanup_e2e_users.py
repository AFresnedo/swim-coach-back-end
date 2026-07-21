"""Delete specific users created by the swim-coach front-end's Playwright e2e suite.

Called by e2e/global-teardown.ts with the exact emails its fixtures created
this run (see e2e/fixtures.ts) — never guesses based on a naming convention,
so it can't miss or misfire on real accounts.

    uv run python -m scripts.cleanup_e2e_users user1@example.com user2@example.com
"""

import sys

from sqlalchemy import delete, select

from app.auth.model import User
from app.database import SessionLocal
from app.goal.model import Goal
from app.profile.model import Profile
from app.swim_time.model import SwimTime


def main(emails: list[str]) -> None:
    if not emails:
        print("No emails given, nothing to clean up.")
        return

    with SessionLocal() as db:
        user_ids = list(db.scalars(select(User.id).where(User.email.in_(emails))))
        if not user_ids:
            print("No matching e2e test users found.")
            return

        db.execute(delete(SwimTime).where(SwimTime.user_id.in_(user_ids)))
        db.execute(delete(Goal).where(Goal.user_id.in_(user_ids)))
        db.execute(delete(Profile).where(Profile.user_id.in_(user_ids)))
        db.execute(delete(User).where(User.id.in_(user_ids)))
        db.commit()
        print(f"Deleted {len(user_ids)} e2e test user(s).")


if __name__ == "__main__":
    main(sys.argv[1:])
