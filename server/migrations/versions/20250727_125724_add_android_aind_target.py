"""add android aind target

Revision ID: a7b9c2d4e5f6
Revises: 162786000c7b
Create Date: 2025-07-27 12:57:24.000000

"""
import os
from typing import Sequence, Union
from datetime import datetime

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7b9c2d4e5f6'
down_revision: Union[str, None] = '162786000c7b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Insert Android AinD target
    op.execute("""
            INSERT INTO targets (
                id, name, type, host, port, username, password, 
                width, height, vnc_path, novnc_port, created_at, updated_at, 
                is_archived, vpn_config, vpn_username, vpn_password, pool_type
            ) VALUES 
            (
                'c8f6d5e3-8c72-5f90-93b5-2f7e0e9d5c38',
                'Android AinD (Native VNC)',
                'vnc',
                'legacy-use-android-aind-target',  -- Use Kubernetes service name
                '5900',
                '',
                '',
                '1280',
                '720',
                'vnc.html',
                '6080',  -- Not used, but keeping for compatibility
                NOW(),
                NOW(),
                false,
                '',
                '',
                '',
                'android-aind'
            )
            ON CONFLICT (id) DO NOTHING
        """)


def downgrade() -> None:
    # Remove Android AinD target
    op.execute("""
        DELETE FROM targets 
        WHERE id = 'c8f6d5e3-8c72-5f90-93b5-2f7e0e9d5c38'
    """)