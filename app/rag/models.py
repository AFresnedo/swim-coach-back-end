from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import CheckConstraint, Float, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import UTCDateTime, VectorBase
from app.enums import (
    INGESTION_REASONS,
    QUALITY_FLAGS,
    SKILL_LEVELS,
    STROKES,
    TOPIC_CATEGORIES,
    IngestionReasonLiteral,
    QualityFlagLiteral,
    SkillLevelLiteral,
    StrokeLiteral,
    TopicCategoryLiteral,
)
from app.model_utils import in_clause, nullable_in_clause, utcnow

# voyage-4-lite's output_dimension. Changing models/dimensions later requires a
# migration (the HNSW index and column width are baked to this size) and a full
# re-embed of any existing rows - not something to change casually.
EMBEDDING_DIMENSION = 512


class KnowledgeChunkMixin:
    """Shared columns for pgvector-backed knowledge-base tables.

    Deliberately a plain column mixin, not a shared table with a domain
    discriminator - see the "Hybrid RAG training-coach endpoint" Trello card for
    why (mixing corpora degrades ANN index quality, and filtered vector search
    over a shared index is a known hard tradeoff). Each domain (SwimKnowledge
    today, a future recovery-plan KB, etc.) gets its own table built from this
    mixin, with its own CheckConstraints and HNSW index in __table_args__.
    """

    id: Mapped[int] = mapped_column(primary_key=True)
    chunk_text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMENSION))

    # Provenance - all populated as structured output on the same ingestion call
    # that already read the fetched content in full (see step 4 of the card).
    source_url: Mapped[str] = mapped_column(Text)
    source_query: Mapped[str] = mapped_column(Text)
    ingested_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    ingestion_reason: Mapped[IngestionReasonLiteral] = mapped_column(String(30))
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_flag: Mapped[QualityFlagLiteral] = mapped_column(String(10))
    quality_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Classification - nullable, forward-compat for the future hybrid-retrieval
    # ticket's metadata routing. topic_category/skill_level are a provisional
    # starter taxonomy, not final - see project memory before building the
    # ingestion prompt that populates them.
    stroke_type: Mapped[StrokeLiteral | None] = mapped_column(String(20), nullable=True)
    topic_category: Mapped[TopicCategoryLiteral | None] = mapped_column(String(30), nullable=True)
    skill_level: Mapped[SkillLevelLiteral | None] = mapped_column(String(20), nullable=True)


class SwimKnowledge(KnowledgeChunkMixin, VectorBase):
    __tablename__ = "swim_knowledge"

    __table_args__ = (
        CheckConstraint(in_clause("ingestion_reason", INGESTION_REASONS), name="ck_swim_knowledge_ingestion_reason"),
        CheckConstraint(in_clause("quality_flag", QUALITY_FLAGS), name="ck_swim_knowledge_quality_flag"),
        CheckConstraint(nullable_in_clause("stroke_type", STROKES), name="ck_swim_knowledge_stroke_type"),
        CheckConstraint(
            nullable_in_clause("topic_category", TOPIC_CATEGORIES), name="ck_swim_knowledge_topic_category"
        ),
        CheckConstraint(nullable_in_clause("skill_level", SKILL_LEVELS), name="ck_swim_knowledge_skill_level"),
        Index(
            "ix_swim_knowledge_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )
