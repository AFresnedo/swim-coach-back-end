import pytest
from sqlalchemy.exc import IntegrityError

from app.goal.model import Goal


def test_defaults(db_session):
    goal = Goal(user_id=1, text="Swim a 50 free under 25 seconds")
    db_session.add(goal)
    db_session.commit()

    assert goal.is_active is True
    assert goal.deactivation_reason is None
    assert goal.created_at is not None


def test_deactivation_reason_rejects_value_outside_enum(db_session):
    goal = Goal(user_id=1, text="Swim a 50 free under 25 seconds", deactivation_reason="changed-my-mind")
    db_session.add(goal)

    with pytest.raises(IntegrityError):
        db_session.commit()
