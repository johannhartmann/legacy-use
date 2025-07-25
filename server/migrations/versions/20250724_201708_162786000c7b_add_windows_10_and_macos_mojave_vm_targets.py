"""add windows 10 and macos mojave vm targets

Revision ID: 162786000c7b
Revises: 450b1b184d8a
Create Date: 2025-07-24 20:17:08.000000

"""
import os
from typing import Sequence, Union
from datetime import datetime

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '162786000c7b'
down_revision: Union[str, None] = '450b1b184d8a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Insert Windows 10 and macOS Mojave VM targets
    op.execute("""
        INSERT INTO targets (
            id, name, type, host, port, username, password, 
            width, height, vnc_path, novnc_port, created_at, updated_at, 
            is_archived, vpn_config, vpn_username, vpn_password, pool_type
        ) VALUES 
        (
            'c7f5e3a9-2d84-4b91-8fa5-3e7c9d5f2b46',
            'Windows 10 VM (KubeVirt)',
            'vnc',
            'legacy-use-windows-10-kubevirt',  -- Use Kubernetes service name
            '5900',
            '',
            '',
            '1920',
            '1080',
            'vnc.html',
            '6080',  -- Standard noVNC port
            NOW(),
            NOW(),
            false,
            '',
            '',
            '',
            'windows-10-vm'
        ),
        (
            'd8a6f4b1-3e95-4c02-9fb6-4d8e0a6c3e57',
            'macOS Mojave VM (KubeVirt)',
            'vnc',
            'legacy-use-macos-mojave-kubevirt',  -- Use Kubernetes service name
            '5900',
            '',
            '',
            '1920',
            '1080',
            'vnc.html',
            '6080',  -- Standard noVNC port
            NOW(),
            NOW(),
            false,
            '',
            '',
            '',
            'macos-mojave-vm'
        )
        ON CONFLICT (id) DO NOTHING
    """)


def downgrade() -> None:
    # Remove Windows 10 and macOS Mojave VM targets
    op.execute("""
        DELETE FROM targets 
        WHERE id IN (
            'c7f5e3a9-2d84-4b91-8fa5-3e7c9d5f2b46',
            'd8a6f4b1-3e95-4c02-9fb6-4d8e0a6c3e57'
        )
    """)