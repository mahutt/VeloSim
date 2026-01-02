"""drop_resources_table

Revision ID: 504983637b01
Revises: a38066d010a1
Create Date: 2026-01-02 00:03:38.891334

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '504983637b01'
down_revision: Union[str, Sequence[str], None] = 'a38066d010a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_table('resources')


def downgrade() -> None:
    """Downgrade schema."""
    op.create_table(
        'resources',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('type', sa.Enum('VEHICLE_DRIVER', name='resourcetype'), nullable=False),
        sa.Column('date_created', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('date_updated', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('route_start_latitude', sa.Float(), nullable=False),
        sa.Column('route_start_longitude', sa.Float(), nullable=False),
        sa.Column('route_end_latitude', sa.Float(), nullable=False),
        sa.Column('route_end_longitude', sa.Float(), nullable=False),
        sa.Column('sim_instance_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['sim_instance_id'], ['sim_instances.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_resources_id'), 'resources', ['id'], unique=False)
