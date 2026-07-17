"""add swim_knowledge table

Revision ID: 10abbec90eff
Revises: 306c260d569b
Create Date: 2026-07-15 11:30:55.097843

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = '10abbec90eff'
down_revision: Union[str, Sequence[str], None] = '306c260d569b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "swim_knowledge",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(512), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("source_query", sa.Text(), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ingestion_reason", sa.String(length=30), nullable=False),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column("quality_flag", sa.String(length=10), nullable=False),
        sa.Column("quality_reason", sa.Text(), nullable=True),
        sa.Column("stroke_type", sa.String(length=20), nullable=True),
        sa.Column("topic_category", sa.String(length=30), nullable=True),
        sa.Column("skill_level", sa.String(length=20), nullable=True),
        sa.CheckConstraint("ingestion_reason IN ('fallback_web_search')", name="ck_swim_knowledge_ingestion_reason"),
        sa.CheckConstraint("quality_flag IN ('pass', 'reject')", name="ck_swim_knowledge_quality_flag"),
        sa.CheckConstraint(
            "skill_level IS NULL OR skill_level IN ('beginner', 'intermediate', 'advanced', 'elite')",
            name="ck_swim_knowledge_skill_level",
        ),
        sa.CheckConstraint(
            "stroke_type IS NULL OR stroke_type IN "
            "('freestyle', 'backstroke', 'breaststroke', 'butterfly', 'individual_medley')",
            name="ck_swim_knowledge_stroke_type",
        ),
        sa.CheckConstraint(
            "topic_category IS NULL OR topic_category IN "
            "('technique', 'drills', 'training_science', 'recovery', 'nutrition', 'race_strategy', 'equipment')",
            name="ck_swim_knowledge_topic_category",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_swim_knowledge_embedding_hnsw",
        "swim_knowledge",
        ["embedding"],
        unique=False,
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Extension is left in place - other objects may depend on it, and
    # CREATE EXTENSION IF NOT EXISTS in upgrade() makes re-running safe either way.
    op.drop_index(
        "ix_swim_knowledge_embedding_hnsw",
        table_name="swim_knowledge",
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.drop_table("swim_knowledge")
