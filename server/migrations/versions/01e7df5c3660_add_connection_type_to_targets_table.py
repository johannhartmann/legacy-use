"""Add connection_type to targets table

Revision ID: 01e7df5c3660
Revises: b8c9d3e4f6a7
Create Date: 2025-07-30 13:05:43.826300

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '01e7df5c3660'
down_revision: Union[str, None] = 'b8c9d3e4f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add connection_type column with default 'pool'
    op.add_column('targets', sa.Column('connection_type', sa.String(), nullable=False, server_default='pool'))
    
    # Update existing targets based on their current configuration
    # Direct connection targets (ones with actual host IPs)
    op.execute("""
        UPDATE targets 
        SET connection_type = 'direct' 
        WHERE host NOT LIKE 'legacy-use-%' 
        AND host NOT LIKE '%kubevirt%'
        AND host NOT IN ('localhost', '127.0.0.1')
    """)
    
    # VM targets (KubeVirt)
    op.execute("""
        UPDATE targets 
        SET connection_type = 'vm' 
        WHERE host LIKE '%kubevirt%'
        OR pool_type LIKE '%-vm'
    """)
    
    # Everything else stays as 'pool' (the default)


def downgrade() -> None:
    op.drop_column('targets', 'connection_type')
