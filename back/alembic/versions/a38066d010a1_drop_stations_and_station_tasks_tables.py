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
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
