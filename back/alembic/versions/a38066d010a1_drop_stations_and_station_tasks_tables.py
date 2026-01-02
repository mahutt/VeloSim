"""drop_stations_and_station_tasks_tables

Revision ID: a38066d010a1
Revises: 44c3c1f26443
Create Date: 2026-01-01 23:33:35.399050

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a38066d010a1'
down_revision: Union[str, Sequence[str], None] = '44c3c1f26443'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop station_tasks table (must drop first due to foreign key to stations)
    op.drop_table('station_tasks')
    # Drop stations table
    op.drop_table('stations')


def downgrade() -> None:
    """Downgrade schema."""
    # Recreate stations table first
    op.create_table(
        'stations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('sim_instance_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['sim_instance_id'], ['sim_instances.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_stations_id'), 'stations', ['id'], unique=False)
    op.create_index(op.f('ix_stations_name'), 'stations', ['name'], unique=False)

    # Recreate station_tasks table
    op.create_table(
        'station_tasks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('type', sa.Enum('BATTERY_SWAP', name='stationtasktype'), nullable=False),
        sa.Column('status', sa.Enum('UNASSIGNED', 'ASSIGNED', 'IN_PROGRESS', 'COMPLETED', 'ABANDONED', name='taskstatus'), nullable=False),
        sa.Column('date_created', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('date_updated', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('station_id', sa.Integer(), nullable=False),
        sa.Column('sim_instance_id', sa.Integer(), nullable=False),
        sa.Column('resource_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['station_id'], ['stations.id']),
        sa.ForeignKeyConstraint(['sim_instance_id'], ['sim_instances.id']),
        sa.ForeignKeyConstraint(['resource_id'], ['resources.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_station_tasks_id'), 'station_tasks', ['id'], unique=False)
