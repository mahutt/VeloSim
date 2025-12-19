"""add sim keyframes table

Revision ID: d957b0e93607
Revises: 77374ce4f9cf
Create Date: 2025-12-18 13:15:58.937490

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd957b0e93607'
down_revision: Union[str, Sequence[str], None] = '77374ce4f9cf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'sim_keyframes',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('sim_instance_id', sa.Integer(), nullable=False),
        sa.Column('sim_seconds_elapsed', sa.Float(), nullable=False),
        sa.Column('frame_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['sim_instance_id'], ['sim_instances.id'], ondelete='CASCADE'),
    )
    op.create_index(op.f('ix_sim_keyframes_id'), 'sim_keyframes', ['id'], unique=False)
    op.create_index(
        'ix_sim_keyframes_instance_time',
        'sim_keyframes',
        ['sim_instance_id', 'sim_seconds_elapsed'],
        unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_sim_keyframes_instance_time', table_name='sim_keyframes')
    op.drop_index(op.f('ix_sim_keyframes_id'), table_name='sim_keyframes')
    op.drop_table('sim_keyframes')
