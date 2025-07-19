"""Add port fields to sessions for container pool support

Revision ID: add_port_fields
Revises: 
Create Date: 2024-01-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_port_fields'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Get database connection
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Get existing columns
    columns = [col['name'] for col in inspector.get_columns('sessions')]
    
    # Add vnc_port column to sessions table if it doesn't exist
    if 'vnc_port' not in columns:
        op.add_column('sessions', sa.Column('vnc_port', sa.String(10), nullable=True))
    
    # Add novnc_port column to sessions table if it doesn't exist
    if 'novnc_port' not in columns:
        op.add_column('sessions', sa.Column('novnc_port', sa.String(10), nullable=True))
    
    # Add error_message column to sessions table for better error tracking if it doesn't exist
    if 'error_message' not in columns:
        op.add_column('sessions', sa.Column('error_message', sa.Text, nullable=True))


def downgrade():
    # Remove the columns
    op.drop_column('sessions', 'error_message')
    op.drop_column('sessions', 'novnc_port')
    op.drop_column('sessions', 'vnc_port')