"""Add n8n_status column to auto_search_config

Revision ID: n8o9p0q1r2s3
Revises: h2i3j4k5l6m7
Create Date: 2025-12-22 18:15:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "n8o9p0q1r2s3"
down_revision = "m6n7o8p9q0r1"
branch_labels = None
depends_on = None


def upgrade():
    # Check if table exists
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()
    
    if "auto_search_config" in existing_tables:
        columns = {col["name"] for col in inspector.get_columns("auto_search_config")}
        
        # Add n8n_status column if it doesn't exist
        if "n8n_status" not in columns:
            # Use batch mode for SQLite compatibility
            with op.batch_alter_table("auto_search_config", schema=None) as batch_op:
                batch_op.add_column(
                    sa.Column("n8n_status", sa.String(), nullable=False, server_default="pending")
                )


def downgrade():
    # Remove n8n_status column
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "auto_search_config" in inspector.get_table_names():
        columns = {col["name"] for col in inspector.get_columns("auto_search_config")}
        if "n8n_status" in columns:
            with op.batch_alter_table("auto_search_config", schema=None) as batch_op:
                batch_op.drop_column("n8n_status")

