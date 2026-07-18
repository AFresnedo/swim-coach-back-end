from datetime import datetime
from typing import ClassVar

from pgvector.sqlalchemy import Vector
from sqlalchemy import Float, Index, Text
from sqlalchemy.orm import Mapped, declared_attr, mapped_column

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
from app.model_utils import enum_column, utcnow

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
    mixin, with its own HNSW index in __table_args__.

    The enum-typed columns are declared_attr so their CHECK constraint names
    (via enum_column) derive from each subclass's own __tablename__ instead of
    being hardcoded here - a plain `col: Mapped[X] = mapped_column(enum_column(...,
    name="ck_swim_knowledge_..."))` would bake the swim_knowledge name into the
    mixin itself, and a second domain table built from this mixin would silently
    inherit those same misnamed constraints.
    """

    # Declared, not assigned - each concrete subclass provides the real value.
    # Only here so the declared_attr methods below can reference cls.__tablename__
    # without pyright flagging it as unknown on this plain (non-DeclarativeBase) mixin.
    __tablename__: ClassVar[str]

    id: Mapped[int] = mapped_column(primary_key=True)
    chunk_text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMENSION))

    # Provenance - all populated as structured output on the same ingestion call
    # that already read the fetched content in full (see step 4 of the card).
    source_url: Mapped[str] = mapped_column(Text)
    source_query: Mapped[str] = mapped_column(Text)
    ingested_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    @declared_attr
    def ingestion_reason(cls) -> Mapped[IngestionReasonLiteral]:  # noqa: N805
        return mapped_column(
            enum_column(*INGESTION_REASONS, name=f"ck_{cls.__tablename__}_ingestion_reason", length=30)
        )

    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    @declared_attr
    def quality_flag(cls) -> Mapped[QualityFlagLiteral]:  # noqa: N805
        return mapped_column(enum_column(*QUALITY_FLAGS, name=f"ck_{cls.__tablename__}_quality_flag", length=10))

    quality_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Classification - nullable, forward-compat for the future hybrid-retrieval
    # ticket's metadata routing. topic_category/skill_level are a provisional
    # starter taxonomy, not final - see project memory before building the
    # ingestion prompt that populates them.
    @declared_attr
    def stroke_type(cls) -> Mapped[StrokeLiteral | None]:  # noqa: N805
        return mapped_column(
            enum_column(*STROKES, name=f"ck_{cls.__tablename__}_stroke_type", length=20), nullable=True
        )

    @declared_attr
    def topic_category(cls) -> Mapped[TopicCategoryLiteral | None]:  # noqa: N805
        return mapped_column(
            enum_column(*TOPIC_CATEGORIES, name=f"ck_{cls.__tablename__}_topic_category", length=30), nullable=True
        )

    @declared_attr
    def skill_level(cls) -> Mapped[SkillLevelLiteral | None]:  # noqa: N805
        return mapped_column(
            enum_column(*SKILL_LEVELS, name=f"ck_{cls.__tablename__}_skill_level", length=20), nullable=True
        )


class SwimKnowledge(KnowledgeChunkMixin, VectorBase):
    __tablename__ = "swim_knowledge"

    __table_args__ = (
        Index(
            "ix_swim_knowledge_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )
