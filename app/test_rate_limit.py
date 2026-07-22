from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException
from limits.errors import StorageError

from app.rate_limit import check_storage, enforce_rate_limit, get_remote_address


def test_get_remote_address_returns_the_client_host():
    request = Mock(client=Mock(host="203.0.113.5"))
    assert get_remote_address(request) == "203.0.113.5"


def test_get_remote_address_falls_back_when_client_is_missing():
    request = Mock(client=None)
    assert get_remote_address(request) == "127.0.0.1"


def test_enforce_rate_limit_allows_requests_under_the_limit():
    enforce_rate_limit(limit_string="2/minute", key="test-under-limit")
    enforce_rate_limit(limit_string="2/minute", key="test-under-limit")


def test_enforce_rate_limit_raises_429_once_the_limit_is_exceeded():
    enforce_rate_limit(limit_string="1/minute", key="test-over-limit")

    with pytest.raises(HTTPException) as exc_info:
        enforce_rate_limit(limit_string="1/minute", key="test-over-limit")

    assert exc_info.value.status_code == 429
    assert exc_info.value.headers is not None
    assert "Retry-After" in exc_info.value.headers


def test_enforce_rate_limit_raises_503_when_the_storage_backend_is_unreachable():
    with patch("app.rate_limit._limiter.hit", side_effect=StorageError(ConnectionError("boom"))):
        with pytest.raises(HTTPException) as exc_info:
            enforce_rate_limit(limit_string="5/minute", key="test-storage-down")

    assert exc_info.value.status_code == 503


def test_check_storage_raises_when_unreachable():
    with patch("app.rate_limit._storage.check", return_value=False):
        with pytest.raises(RuntimeError):
            check_storage()
