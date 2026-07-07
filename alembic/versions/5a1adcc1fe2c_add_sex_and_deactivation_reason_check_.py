"""add sex and deactivation_reason check constraints

Revision ID: 5a1adcc1fe2c
Revises: 0556b49ea11e
Create Date: 2026-07-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '5a1adcc1fe2c'
down_revision: Union[str, Sequence[str], None] = '0556b49ea11e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_check_constraint(
        "ck_profiles_sex",
        "profiles",
        "sex IN ('male', 'female', 'prefer_not_to_say')",
    )
    op.create_check_constraint(
        "ck_goals_deactivation_reason",
        "goals",
        "deactivation_reason IS NULL OR deactivation_reason IN ('reached', 'abandoned', 'other')",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("ck_goals_deactivation_reason", "goals", type_="check")
    op.drop_constraint("ck_profiles_sex", "profiles", type_="check")
