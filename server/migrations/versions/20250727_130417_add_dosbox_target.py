"""add dosbox target

Revision ID: b8c9d3e4f6a7
Revises: a7b9c2d4e5f6
Create Date: 2025-07-27 13:04:17.000000

"""
import os
from typing import Sequence, Union
from datetime import datetime

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8c9d3e4f6a7'
down_revision: Union[str, None] = 'a7b9c2d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Insert DOSBox target
    op.execute("""
            INSERT INTO targets (
                id, name, type, host, port, username, password, 
                width, height, vnc_path, novnc_port, created_at, updated_at, 
                is_archived, vpn_config, vpn_username, vpn_password, pool_type
            ) VALUES 
            (
                'd9a7e4f5-9d83-6fa1-a4c6-3f8f1f0e6d49',
                'DOSBox (DOS Programs)',
                'vnc',
                'legacy-use-dosbox-target',  -- Use Kubernetes service name
                '5900',
                '',
                '',
                '1024',
                '768',
                'vnc.html',
                '6080',  -- Not used, but keeping for compatibility
                NOW(),
                NOW(),
                false,
                '',
                '',
                '',
                'dosbox'
            )
            ON CONFLICT (id) DO NOTHING
        """)


def downgrade() -> None:
    # Remove DOSBox target
    op.execute("""
        DELETE FROM targets 
        WHERE id = 'd9a7e4f5-9d83-6fa1-a4c6-3f8f1f0e6d49'
    """)