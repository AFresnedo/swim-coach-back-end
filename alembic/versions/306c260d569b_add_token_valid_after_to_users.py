"""add token_valid_after to users

Revision ID: 306c260d569b
Revises: 5a1adcc1fe2c
Create Date: 2026-07-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '306c260d569b'
down_revision: Union[str, Sequence[str], None] = '5a1adcc1fe2c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # NOT NULL, backfilled via server_default (computed once in the DB rather
    # than from this process's clock) rather than left NULL: deploying this
    # column is meant to revoke every token that's already outstanding, not
    # just ones issued from this point forward. The server_default is then
    # dropped so it doesn't linger and affect new rows - new registrations get
    # their own cutoff (registration time) via the model's default instead.
    op.add_column(
        "users",
        sa.Column("token_valid_after", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.alter_column("users", "token_valid_after", server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "token_valid_after")
