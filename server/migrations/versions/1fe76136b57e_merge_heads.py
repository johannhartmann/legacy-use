"""merge_heads

Revision ID: 1fe76136b57e
Revises: 3814b7855961, add_port_fields
Create Date: 2025-07-16 17:16:30.218830

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1fe76136b57e'
down_revision: Union[str, None] = ('3814b7855961', 'add_port_fields')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
