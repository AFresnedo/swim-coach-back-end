from contextlib import contextmanager
from unittest.mock import Mock, patch

import pytest
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Session

from app.database import get_db
from app.profile.model import Profile
from app.user.model import User


@contextmanager
def _spy_on_session_calls():
    manager = Mock()
    with (
        patch.object(Session, "rollback", wraps=Session.rollback, autospec=True) as rollback,
        patch.object(Session, "close", wraps=Session.close, autospec=True) as close,
    ):
        manager.attach_mock(rollback, "rollback")
        manager.attach_mock(close, "close")
        yield manager


def test_get_db_closes_without_rollback_on_normal_completion():
    with _spy_on_session_calls() as manager:
        gen = get_db()
        next(gen)

        with pytest.raises(StopIteration):
            next(gen)

        assert [call[0] for call in manager.mock_calls] == ["close"]


def test_get_db_rolls_back_before_closing_on_exception():
    with _spy_on_session_calls() as manager:
        gen = get_db()
        next(gen)

        with pytest.raises(ValueError):
            gen.throw(ValueError("boom"))

        assert [call[0] for call in manager.mock_calls] == ["rollback", "close"]


def _unique_signatures(model: type) -> set[tuple[str, ...]]:
    signatures = {
        tuple(col.name for col in constraint.columns)
        for constraint in model.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    signatures |= {tuple(col.name for col in index.columns) for index in model.__table__.indexes if index.unique}
    return signatures


def test_upsert_conflict_targets_are_each_table_s_only_unique_constraint():
    # auth.register and profile.upsert_profile each run a single INSERT ... ON
    # CONFLICT that names ONE conflict target (email / user_id) and absorbs a
    # collision only on that target - a violation of any *other* unique constraint
    # would bypass ON CONFLICT and surface as a 500 instead of a clean 4xx. That's
    # safe only while each target is its table's sole non-PK unique constraint.
    # If this test fails because you added a unique constraint, revisit those two
    # endpoints before updating the expected set here.
    assert _unique_signatures(User) == {("email",)}
    assert _unique_signatures(Profile) == {("user_id",)}
