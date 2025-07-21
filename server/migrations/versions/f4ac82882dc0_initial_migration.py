"""Initial migration

Revision ID: f4ac82882dc0
Revises:
Create Date: 2025-02-28 17:52:46.723805

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f4ac82882dc0'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable UUID extension for PostgreSQL
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    
    # Create targets table
    op.create_table('targets',
        sa.Column('id', sa.Text(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('host', sa.String(), nullable=False),
        sa.Column('port', sa.String(), nullable=True),
        sa.Column('username', sa.String(), nullable=True),
        sa.Column('password', sa.String(), nullable=False),
        sa.Column('vpn_config', sa.String(), nullable=True),
        sa.Column('vpn_username', sa.String(), nullable=True),
        sa.Column('vpn_password', sa.String(), nullable=True),
        sa.Column('width', sa.String(), nullable=False, server_default='1024'),
        sa.Column('height', sa.String(), nullable=False, server_default='768'),
        sa.Column('vnc_path', sa.String(), nullable=False, server_default='vnc.html'),
        sa.Column('novnc_port', sa.String(), nullable=False, server_default='6080'),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('is_archived', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('tailscale_authkey', sa.String(), nullable=True),
        sa.Column('pool_type', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create sessions table
    op.create_table('sessions',
        sa.Column('id', sa.Text(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('target_id', sa.Text(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='created'),
        sa.Column('state', sa.String(), nullable=False, server_default='initializing'),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('is_archived', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('archive_reason', sa.String(), nullable=True),
        sa.Column('last_job_time', sa.TIMESTAMP(), nullable=True),
        sa.Column('container_id', sa.String(), nullable=True),
        sa.Column('container_ip', sa.String(), nullable=True),
        sa.Column('vnc_port', sa.String(length=10), nullable=True),
        sa.Column('novnc_port', sa.String(length=10), nullable=True),
        sa.ForeignKeyConstraint(['target_id'], ['targets.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create api_definitions table
    op.create_table('api_definitions',
        sa.Column('id', sa.Text(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=True, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=True, server_default=sa.text('NOW()')),
        sa.Column('is_archived', sa.Boolean(), nullable=True, server_default='false'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    
    # Create api_definition_versions table
    op.create_table('api_definition_versions',
        sa.Column('id', sa.Text(), nullable=False),
        sa.Column('api_definition_id', sa.Text(), nullable=False),
        sa.Column('version_number', sa.String(), nullable=False),
        sa.Column('parameters', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('prompt', sa.String(), nullable=False),
        sa.Column('prompt_cleanup', sa.String(), nullable=False),
        sa.Column('response_example', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=True, server_default=sa.text('NOW()')),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.ForeignKeyConstraint(['api_definition_id'], ['api_definitions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create jobs table
    op.create_table('jobs',
        sa.Column('id', sa.Text(), nullable=False),
        sa.Column('target_id', sa.Text(), nullable=False),
        sa.Column('session_id', sa.Text(), nullable=True),
        sa.Column('api_name', sa.String(), nullable=True),
        sa.Column('api_definition_version_id', sa.Text(), nullable=True),
        sa.Column('parameters', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(), nullable=True, server_default='pending'),
        sa.Column('result', sa.JSON(), nullable=True),
        sa.Column('error', sa.String(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=True, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=True, server_default=sa.text('NOW()')),
        sa.Column('completed_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('total_input_tokens', sa.Integer(), nullable=True),
        sa.Column('total_output_tokens', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['api_definition_version_id'], ['api_definition_versions.id'], ),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ),
        sa.ForeignKeyConstraint(['target_id'], ['targets.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create job_logs table
    op.create_table('job_logs',
        sa.Column('id', sa.Text(), nullable=False),
        sa.Column('job_id', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.TIMESTAMP(), nullable=True, server_default=sa.text('NOW()')),
        sa.Column('log_type', sa.String(), nullable=True),
        sa.Column('content', sa.JSON(), nullable=True),
        sa.Column('content_trimmed', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create job_messages table
    op.create_table('job_messages',
        sa.Column('id', sa.Text(), nullable=False),
        sa.Column('job_id', sa.Text(), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('message_content', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=True, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_job_messages_job_id', 'job_messages', ['job_id'], unique=False)
    op.create_index('ix_jobmessage_job_id_sequence', 'job_messages', ['job_id', 'sequence'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_jobmessage_job_id_sequence', table_name='job_messages')
    op.drop_index('ix_job_messages_job_id', table_name='job_messages')
    op.drop_table('job_messages')
    op.drop_table('job_logs')
    op.drop_table('jobs')
    op.drop_table('api_definition_versions')
    op.drop_table('api_definitions')
    op.drop_table('sessions')
    op.drop_table('targets')
