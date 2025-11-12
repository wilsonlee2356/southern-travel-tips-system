"""Add travel_class and direct_flight to auto_search

Revision ID: b3c4d5e6f7a8
Revises: a1b2c3d4e5f6
Create Date: 2025-11-12 16:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "b3c4d5e6f7a8"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "auto_search",
        sa.Column("travel_class", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "auto_search",
        sa.Column(
            "direct_flight",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )

    op.execute(
        "UPDATE auto_search SET travel_class = 0 WHERE travel_class IS NULL"
    )
    op.execute(
        "UPDATE auto_search SET direct_flight = 0 WHERE direct_flight IS NULL"
    )

    with op.batch_alter_table("auto_search") as batch_op:
        batch_op.alter_column("travel_class", server_default=None)
        batch_op.alter_column("direct_flight", server_default=None)


def downgrade():
    with op.batch_alter_table("auto_search") as batch_op:
        batch_op.drop_column("direct_flight")
        batch_op.drop_column("travel_class")

