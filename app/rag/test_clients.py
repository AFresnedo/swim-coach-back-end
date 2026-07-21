from unittest.mock import MagicMock

import pytest

from app.rag.clients import extract_response_text


def test_returns_text_from_a_text_block():
    response = MagicMock(content=[MagicMock(type="text", text="the answer")])
    assert extract_response_text(response, source="test") == "the answer"


def test_skips_leading_non_text_blocks():
    response = MagicMock(content=[MagicMock(type="thinking", thinking=""), MagicMock(type="text", text="the answer")])
    assert extract_response_text(response, source="test") == "the answer"


def test_raises_when_no_text_block_is_present():
    response = MagicMock(content=[MagicMock(type="thinking", thinking="")], stop_reason="max_tokens")

    with pytest.raises(RuntimeError, match="max_tokens"):
        extract_response_text(response, source="test")
