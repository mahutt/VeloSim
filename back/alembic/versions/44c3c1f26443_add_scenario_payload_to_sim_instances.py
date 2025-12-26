"""add_scenario_payload_to_sim_instances

Revision ID: 44c3c1f26443
Revises: 90070ebfe1c8
Create Date: 2025-12-23 12:42:14.108578

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '44c3c1f26443'
down_revision: Union[str, Sequence[str], None] = '90070ebfe1c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'sim_instances',
        sa.Column(
            'scenario_payload',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True
        )
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('sim_instances', 'scenario_payload')
