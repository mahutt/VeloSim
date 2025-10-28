"""add scenario model

Revision ID: 77374ce4f9cf
Revises: 8f170126dde9
Create Date: 2025-11-02 17:11:32.023859
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '77374ce4f9cf'
down_revision = '8f170126dde9'
branch_labels = None
depends_on = None

def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'scenarios',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('content', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('date_created', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('date_updated', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
    )
    op.create_index(op.f('ix_scenarios_id'), 'scenarios', ['id'], unique=False)

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_scenarios_id'), table_name='scenarios')
    op.drop_table('scenarios')
