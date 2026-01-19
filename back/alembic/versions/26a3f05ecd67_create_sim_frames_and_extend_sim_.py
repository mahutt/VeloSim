"""create_sim_frames_and_extend_sim_instances

Revision ID: 26a3f05ecd67
Revises: 504983637b01
Create Date: 2026-01-18 21:30:24.138789

This migration:
1. Creates new sim_frames table with is_key and seq_number columns
2. Migrates existing data from sim_keyframes (all existing frames are keyframes)
3. Drops the sim_keyframes table
4. Adds playback_capable, name, parent_sim_instance_id, branch_keyframe_seq to sim_instances
   - Existing instances get playback_capable=false (legacy)
   - New instances will default to playback_capable=true
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '26a3f05ecd67'
down_revision: Union[str, Sequence[str], None] = '504983637b01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Step 1: Create new sim_frames table
    op.create_table('sim_frames',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sim_instance_id', sa.Integer(), nullable=False),
        sa.Column('seq_number', sa.Integer(), nullable=False),
        sa.Column('sim_seconds_elapsed', sa.Float(), nullable=False),
        sa.Column('frame_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('is_key', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['sim_instance_id'], ['sim_instances.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('sim_instance_id', 'seq_number', name='uq_sim_frames_instance_seq')
    )
    op.create_index('ix_sim_frames_created_at', 'sim_frames', ['created_at'], unique=False)
    op.create_index(op.f('ix_sim_frames_id'), 'sim_frames', ['id'], unique=False)
    op.create_index('ix_sim_frames_instance_time', 'sim_frames', ['sim_instance_id', 'sim_seconds_elapsed'], unique=False)
    op.create_index('ix_sim_frames_is_key', 'sim_frames', ['sim_instance_id', 'is_key'], unique=False)

    # Step 2: Migrate existing data from sim_keyframes to sim_frames
    # All existing keyframes are keyframes (is_key=true)
    # We use ROW_NUMBER() to generate seq_number for existing records
    op.execute("""
        INSERT INTO sim_frames (sim_instance_id, seq_number, sim_seconds_elapsed, frame_data, is_key, created_at)
        SELECT
            sim_instance_id,
            ROW_NUMBER() OVER (PARTITION BY sim_instance_id ORDER BY sim_seconds_elapsed, id) - 1 AS seq_number,
            sim_seconds_elapsed,
            frame_data,
            true AS is_key,
            created_at
        FROM sim_keyframes
    """)

    # Step 3: Drop old sim_keyframes table
    op.drop_index('ix_sim_keyframes_instance_time', table_name='sim_keyframes')
    op.drop_index(op.f('ix_sim_keyframes_id'), table_name='sim_keyframes')
    op.drop_index('ix_sim_keyframes_created_at', table_name='sim_keyframes')
    op.drop_table('sim_keyframes')

    # Step 4: Extend sim_instances table
    op.add_column('sim_instances', sa.Column('name', sa.String(length=255), nullable=True))
    op.add_column('sim_instances', sa.Column(
        'playback_capable',
        sa.Boolean(),
        nullable=False,
        server_default=sa.text('false')  # Existing instances are legacy (not playback capable)
    ))
    op.add_column('sim_instances', sa.Column('parent_sim_instance_id', sa.Integer(), nullable=True))
    op.add_column('sim_instances', sa.Column('branch_keyframe_seq', sa.Integer(), nullable=True))

    # Add foreign key for parent_sim_instance_id with proper name
    op.create_foreign_key(
        'fk_sim_instances_parent',
        'sim_instances',
        'sim_instances',
        ['parent_sim_instance_id'],
        ['id'],
        ondelete='SET NULL'
    )

    # Create index for querying child instances
    op.create_index(
        'ix_sim_instances_parent_id',
        'sim_instances',
        ['parent_sim_instance_id'],
        unique=False
    )

    # Step 5: Update server_default for playback_capable to true for future inserts
    # (existing rows already have false from the migration)
    op.alter_column(
        'sim_instances',
        'playback_capable',
        server_default=sa.text('true')
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Step 1: Recreate sim_keyframes table
    op.create_table('sim_keyframes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sim_instance_id', sa.Integer(), nullable=False),
        sa.Column('sim_seconds_elapsed', sa.Float(), nullable=False),
        sa.Column('frame_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['sim_instance_id'], ['sim_instances.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_sim_keyframes_created_at', 'sim_keyframes', ['created_at'], unique=False)
    op.create_index(op.f('ix_sim_keyframes_id'), 'sim_keyframes', ['id'], unique=False)
    op.create_index('ix_sim_keyframes_instance_time', 'sim_keyframes', ['sim_instance_id', 'sim_seconds_elapsed'], unique=False)

    # Step 2: Migrate keyframes back (only is_key=true frames)
    op.execute("""
        INSERT INTO sim_keyframes (sim_instance_id, sim_seconds_elapsed, frame_data, created_at)
        SELECT sim_instance_id, sim_seconds_elapsed, frame_data, created_at
        FROM sim_frames
        WHERE is_key = true
    """)

    # Step 3: Remove sim_instances extensions
    op.drop_index('ix_sim_instances_parent_id', table_name='sim_instances')
    op.drop_constraint('fk_sim_instances_parent', 'sim_instances', type_='foreignkey')
    op.drop_column('sim_instances', 'branch_keyframe_seq')
    op.drop_column('sim_instances', 'parent_sim_instance_id')
    op.drop_column('sim_instances', 'playback_capable')
    op.drop_column('sim_instances', 'name')

    # Step 4: Drop sim_frames table
    op.drop_index('ix_sim_frames_is_key', table_name='sim_frames')
    op.drop_index('ix_sim_frames_instance_time', table_name='sim_frames')
    op.drop_index(op.f('ix_sim_frames_id'), table_name='sim_frames')
    op.drop_index('ix_sim_frames_created_at', table_name='sim_frames')
    op.drop_table('sim_frames')
