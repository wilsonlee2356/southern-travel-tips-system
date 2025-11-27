"""Add airport table

Revision ID: i3j4k5l6m7n8
Revises: h2i3j4k5l6m7
Create Date: 2025-01-15 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "i3j4k5l6m7n8"
down_revision = "h2i3j4k5l6m7"
branch_labels = None
depends_on = None

# This migration merges the flight pricing branch with the main branch
# If you get an overlap error, you may need to manually mark h2i3j4k5l6m7 as applied first


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()
    
    if "airport" not in tables:
        # Table doesn't exist, create it with all columns
        op.create_table(
            "airport",
            sa.Column("airport_id", sa.String(), primary_key=True),
            sa.Column("iata", sa.String(), nullable=False),
            sa.Column("airport_name", sa.Text(), nullable=False),
            sa.Column("place_name", sa.Text(), nullable=False),
            sa.Column("display_name", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
    else:
        # Table exists, check if columns are missing and add them
        existing_columns = {col["name"] for col in inspector.get_columns("airport")}
        
        if "place_name" not in existing_columns:
            op.add_column("airport", sa.Column("place_name", sa.Text(), nullable=True))
            op.execute("UPDATE airport SET place_name = '' WHERE place_name IS NULL")
            # For SQLite, we can't alter column to make it non-nullable, but that's okay
            bind = op.get_bind()
            if bind.dialect.name != "sqlite":
                op.alter_column("airport", "place_name", nullable=False)
        
        if "display_name" not in existing_columns:
            op.add_column("airport", sa.Column("display_name", sa.Text(), nullable=True))
            op.execute("UPDATE airport SET display_name = '' WHERE display_name IS NULL")
            bind = op.get_bind()
            if bind.dialect.name != "sqlite":
                op.alter_column("airport", "display_name", nullable=False)


def downgrade():
    op.drop_table("airport")

