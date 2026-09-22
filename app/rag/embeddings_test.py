from unittest.mock import MagicMock, patch

from app.rag.embeddings import VOYAGE_EMBED_MODEL, embed_documents, embed_query
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


def test_embed_documents_returns_all_embeddings_and_uses_document_input_type():
    fake_result = MagicMock()
    fake_result.embeddings = [[0.1] * EMBEDDING_DIMENSION, [0.2] * EMBEDDING_DIMENSION]

    with patch("app.rag.embeddings.voyage_client.embed", return_value=fake_result) as mock_embed:
        vectors = embed_documents(["chunk one", "chunk two"])

    assert vectors == [[0.1] * EMBEDDING_DIMENSION, [0.2] * EMBEDDING_DIMENSION]
    mock_embed.assert_called_once_with(
        ["chunk one", "chunk two"],
        model=VOYAGE_EMBED_MODEL,
        input_type="document",
        output_dimension=EMBEDDING_DIMENSION,
    )


def test_embed_documents_returns_empty_list_for_no_texts():
    with patch("app.rag.embeddings.voyage_client.embed") as mock_embed:
        vectors = embed_documents([])

    assert vectors == []
    mock_embed.assert_not_called()
