"""Add flight pricing tables

Revision ID: f6c3c2b1d4e5
Revises: d31026856c01
Create Date: 2025-11-12 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "f6c3c2b1d4e5"
down_revision = "d31026856c01"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "airline",
        sa.Column("airline_id", sa.String(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "flight_route",
        sa.Column("route_id", sa.String(), primary_key=True),
        sa.Column("from_place", sa.String(length=10), nullable=False),
        sa.Column("to_place", sa.String(length=10), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "price",
        sa.Column("price_id", sa.String(), primary_key=True),
        sa.Column(
            "route_id",
            sa.String(),
            sa.ForeignKey("flight_route.route_id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "airline_id",
            sa.String(),
            sa.ForeignKey("airline.airline_id"),
            nullable=False,
            index=True,
        ),
        sa.Column("departure_date", sa.DateTime(), nullable=False),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column(
            "is_lowest_price",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )


def downgrade():
    op.drop_table("price")
    op.drop_table("flight_route")
    op.drop_table("airline")

