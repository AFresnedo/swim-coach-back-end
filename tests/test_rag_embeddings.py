from unittest.mock import MagicMock, patch

from app.rag.embeddings import VOYAGE_EMBED_MODEL, embed_query
from app.rag.models import EMBEDDING_DIMENSION


def test_embed_query_returns_first_embedding_and_uses_query_input_type():
    fake_result = MagicMock()
    fake_result.embeddings = [[0.1] * EMBEDDING_DIMENSION]

    with patch("app.rag.embeddings.voyage_client.embed", return_value=fake_result) as mock_embed:
        vector = embed_query("how do i improve my flip turns?")

    assert vector == [0.1] * EMBEDDING_DIMENSION
    mock_embed.assert_called_once_with(
        ["how do i improve my flip turns?"],
        model=VOYAGE_EMBED_MODEL,
        input_type="query",
        output_dimension=EMBEDDING_DIMENSION,
    )
