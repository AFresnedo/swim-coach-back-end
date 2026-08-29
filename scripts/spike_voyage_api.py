"""Ad-hoc check that VOYAGE_API_KEY is wired up correctly end-to-end, using the
real app.rag.embeddings functions (no mocks) - same style as
scripts/verify_training_ask.py but scoped to just the Voyage AI leg of the
pipeline, prompted by swapping in an "al-" (MongoDB Atlas-issued) key in place
of the "pa-" (Voyage-issued) one the .env.example placeholder implied.

Exercises both sides of Voyage's asymmetric embedding (embed_query vs
embed_documents, see app/rag/embeddings.py) and checks the result isn't just
non-erroring but semantically sane: a query's embedding should cosine-score
higher against an on-topic passage than an off-topic one. Also prints which
base URL the client resolved to (ai.mongodb.com for an "al-" key,
api.voyageai.com for a "pa-" one - see voyageai/util.py's
get_default_base_url), since that's exactly the thing this key swap could get
wrong silently.

Requires a real VOYAGE_API_KEY in .env - this makes a real, billed API call.

    uv run python -m scripts.spike_voyage_api
"""

import math

from app.rag.clients import voyage_client
from app.rag.embeddings import embed_documents, embed_query
from app.rag.models import EMBEDDING_DIMENSION

_QUESTION = "What's a good drill for improving my freestyle catch?"
_ON_TOPIC_PASSAGE = (
    "The catch-up drill has swimmers keep one hand extended forward while the "
    "other completes a full stroke cycle, emphasizing a high-elbow catch before "
    "the recovering hand takes over."
)
_OFF_TOPIC_PASSAGE = "Preheat the oven to 450F and let the pizza dough rest for twenty minutes before shaping."


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    return dot / (norm_a * norm_b)


def main() -> None:
    base_url = voyage_client._params["base_url"]
    print(f"Voyage client base_url: {base_url}\n")

    query_embedding = embed_query(_QUESTION)
    print(f"embed_query dimension: {len(query_embedding)} (expected {EMBEDDING_DIMENSION})")
    assert len(query_embedding) == EMBEDDING_DIMENSION

    on_topic_embedding, off_topic_embedding = embed_documents([_ON_TOPIC_PASSAGE, _OFF_TOPIC_PASSAGE])
    print(f"embed_documents dimension: {len(on_topic_embedding)} (expected {EMBEDDING_DIMENSION})")
    assert len(on_topic_embedding) == EMBEDDING_DIMENSION

    on_topic_score = _cosine_similarity(query_embedding, on_topic_embedding)
    off_topic_score = _cosine_similarity(query_embedding, off_topic_embedding)

    print(f"\nQuestion: {_QUESTION!r}")
    print(f"  cosine similarity vs on-topic passage:  {on_topic_score:.4f}")
    print(f"  cosine similarity vs off-topic passage: {off_topic_score:.4f}")

    if on_topic_score > off_topic_score:
        print("\nPASS: on-topic passage scored higher - embeddings look semantically sane.")
    else:
        print("\nFAIL: off-topic passage scored higher or equal - something is wrong.")


if __name__ == "__main__":
    main()
