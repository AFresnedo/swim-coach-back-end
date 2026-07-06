"""add swim_times table

Revision ID: 0556b49ea11e
Revises: b5cd6ffca12b
Create Date: 2026-07-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0556b49ea11e'
down_revision: Union[str, Sequence[str], None] = 'b5cd6ffca12b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('swim_times',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('date', sa.Date(), nullable=False),
    sa.Column('stroke', sa.String(length=20), nullable=False),
    sa.Column('course', sa.String(length=3), nullable=False),
    sa.Column('length', sa.Integer(), nullable=False),
    sa.Column('attempt_number', sa.Integer(), nullable=False),
    sa.Column('time_seconds', sa.Float(), nullable=False),
    sa.Column('is_official', sa.Boolean(), nullable=False),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("stroke IN ('freestyle', 'backstroke', 'breaststroke', 'butterfly', 'individual_medley')", name='ck_swim_times_stroke'),
    sa.CheckConstraint("course IN ('scy', 'scm', 'lcm')", name='ck_swim_times_course'),
    sa.CheckConstraint('length > 0', name='ck_swim_times_length_positive'),
    sa.CheckConstraint('time_seconds > 0', name='ck_swim_times_time_positive'),
    sa.CheckConstraint('attempt_number > 0', name='ck_swim_times_attempt_number_positive'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(
        op.f('ix_swim_times_user_id_date_created_at_id'),
        'swim_times',
        ['user_id', 'date', 'created_at', 'id'],
        unique=False,
    )
    op.create_index(op.f('ix_swim_times_user_id_stroke'), 'swim_times', ['user_id', 'stroke'], unique=False)
    op.create_index(op.f('ix_swim_times_user_id_course'), 'swim_times', ['user_id', 'course'], unique=False)
    op.create_index(op.f('ix_swim_times_user_id_length'), 'swim_times', ['user_id', 'length'], unique=False)
    op.create_index(
        op.f('ix_swim_times_user_id_is_official'), 'swim_times', ['user_id', 'is_official'], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_swim_times_user_id_is_official'), table_name='swim_times')
    op.drop_index(op.f('ix_swim_times_user_id_length'), table_name='swim_times')
    op.drop_index(op.f('ix_swim_times_user_id_course'), table_name='swim_times')
    op.drop_index(op.f('ix_swim_times_user_id_stroke'), table_name='swim_times')
    op.drop_index(op.f('ix_swim_times_user_id_date_created_at_id'), table_name='swim_times')
    op.drop_table('swim_times')
