from unittest.mock import MagicMock, patch

from app.rag.clean import clean_fetched_text


def test_clean_fetched_text_returns_stripped_response_text():
    fake_text_block = MagicMock(type="text", text="  Just the article body.  ")
    fake_response = MagicMock(content=[fake_text_block])

    with patch("app.rag.clean.anthropic_client.messages.create", return_value=fake_response) as mock_create:
        result = clean_fetched_text("nav links\n\nJust the article body.\n\nfooter links")

    assert result == "Just the article body."
    call_kwargs = mock_create.call_args.kwargs
    assert call_kwargs["messages"] == [
        {"role": "user", "content": "nav links\n\nJust the article body.\n\nfooter links"}
    ]
