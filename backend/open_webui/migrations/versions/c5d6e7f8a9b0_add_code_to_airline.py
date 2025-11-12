"""Add code column to airline table

Revision ID: c5d6e7f8a9b0
Revises: b3c4d5e6f7a8
Create Date: 2025-11-12 16:25:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "c5d6e7f8a9b0"
down_revision = "b3c4d5e6f7a8"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "airline",
        sa.Column("code", sa.String(length=10), nullable=True),
    )
    op.create_index("ix_airline_code", "airline", ["code"], unique=False)


def downgrade():
    op.drop_index("ix_airline_code", table_name="airline")
    op.drop_column("airline", "code")

