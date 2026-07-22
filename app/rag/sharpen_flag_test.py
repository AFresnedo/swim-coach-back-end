from unittest.mock import MagicMock, patch

import redis

from app.rag.sharpen_flag import FALLBACK_ENABLED, is_sharpen_enabled


def test_fallback_enabled_is_false():
    assert FALLBACK_ENABLED is False


def test_is_sharpen_enabled_false_when_client_is_none():
    with patch("app.rag.sharpen_flag._redis_client", None):
        assert is_sharpen_enabled() is False


def test_is_sharpen_enabled_false_when_key_unset():
    fake_client = MagicMock()
    fake_client.get.return_value = None
    with patch("app.rag.sharpen_flag._redis_client", fake_client):
        assert is_sharpen_enabled() is False


def test_is_sharpen_enabled_true_when_key_is_one():
    fake_client = MagicMock()
    fake_client.get.return_value = "1"
    with patch("app.rag.sharpen_flag._redis_client", fake_client):
        assert is_sharpen_enabled() is True


def test_is_sharpen_enabled_false_when_key_is_other_value():
    fake_client = MagicMock()
    fake_client.get.return_value = "0"
    with patch("app.rag.sharpen_flag._redis_client", fake_client):
        assert is_sharpen_enabled() is False


def test_is_sharpen_enabled_false_when_redis_unreachable():
    fake_client = MagicMock()
    fake_client.get.side_effect = redis.ConnectionError("connection refused")
    with patch("app.rag.sharpen_flag._redis_client", fake_client):
        assert is_sharpen_enabled() is False


def test_module_import_does_not_crash_on_memory_url(monkeypatch):
    # settings.redis_url is "memory://" in this test process (see conftest.py) -
    # importing the module (which constructs _redis_client at import time) must
    # not raise, even though redis.Redis.from_url() rejects that scheme.
    import importlib

    import app.rag.sharpen_flag as module

    importlib.reload(module)
    assert module._redis_client is None
