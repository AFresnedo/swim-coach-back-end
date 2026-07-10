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
    # Tokens issued before this time are revoked. Existing rows are backfilled
    # with the current time via server_default; the default is left in place
    # afterward (rather than dropped) so it also covers any insert made by an
    # old app instance that doesn't know about this column yet, e.g. during a
    # deploy where the migration runs before every instance is upgraded.
    op.add_column(
        "users",
        sa.Column("token_valid_after", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "token_valid_after")
