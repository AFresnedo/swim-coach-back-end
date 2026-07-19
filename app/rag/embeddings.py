"""Step 2 (and the Step 3b re-embed) of the hybrid RAG training-coach
pipeline: turn text into a vector Postgres can cosine-compare against
SwimKnowledge.chunk_text embeddings (see the "Hybrid RAG training-coach
endpoint" Trello card).
"""

from app.rag.clients import voyage_client
from app.rag.models import EMBEDDING_DIMENSION

# Paired with EMBEDDING_DIMENSION in app/rag/models.py - both are baked into
# the HNSW index and column width, so changing either requires a migration
# and a full re-embed of existing rows.
VOYAGE_EMBED_MODEL = "voyage-4-lite"


def embed_query(text: str) -> list[float]:
    """Embed a single search query for cosine search against SwimKnowledge.

    input_type="query" is Voyage's asymmetric-embedding mode: query text and
    document text are encoded differently so a short question still lands
    close to a longer matching passage. Ingestion (chunking web-fallback
    content into SwimKnowledge, step 4) must embed with input_type="document"
    to match - any future ingestion helper needs to
    use the other side of this asymmetry, not this function.
    """
    result = voyage_client.embed(
        [text],
        model=VOYAGE_EMBED_MODEL,
        input_type="query",
        output_dimension=EMBEDDING_DIMENSION,
    )
    return result.embeddings[0]
