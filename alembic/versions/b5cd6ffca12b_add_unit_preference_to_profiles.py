"""add unit_preference to profiles

Revision ID: b5cd6ffca12b
Revises: 6d8532874f4d
Create Date: 2026-07-06 05:54:35.894546

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b5cd6ffca12b'
down_revision: Union[str, Sequence[str], None] = '6d8532874f4d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "profiles",
        sa.Column("unit_preference", sa.String(length=10), nullable=False, server_default="metric"),
    )
    op.alter_column("profiles", "unit_preference", server_default=None)
    op.create_check_constraint(
        "ck_profiles_unit_preference",
        "profiles",
        "unit_preference IN ('metric', 'imperial')",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("ck_profiles_unit_preference", "profiles", type_="check")
    op.drop_column("profiles", "unit_preference")
