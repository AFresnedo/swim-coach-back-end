from contextlib import contextmanager
from unittest.mock import Mock, patch

import pytest
from sqlalchemy.orm import Session

from app.database import get_db


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
