"""Add auto_search table and update price references

Revision ID: a1b2c3d4e5f6
Revises: f6c3c2b1d4e5
Create Date: 2025-11-12 15:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "a1b2c3d4e5f6"
down_revision = "f6c3c2b1d4e5"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "auto_search",
        sa.Column("auto_search_id", sa.String(), primary_key=True),
        sa.Column("route_id", sa.String(), nullable=False),
        sa.Column("airline_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["route_id"], ["flight_route.route_id"]),
        sa.ForeignKeyConstraint(["airline_id"], ["airline.airline_id"]),
    )

    # Drop old price indexes/table
    with op.batch_alter_table("price") as batch_op:
        try:
            batch_op.drop_index("ix_price_route_id")
        except sa.exc.OperationalError:
            pass
        try:
            batch_op.drop_index("ix_price_airline_id")
        except sa.exc.OperationalError:
            pass
    op.drop_table("price")

    op.create_table(
        "price",
        sa.Column("price_id", sa.String(), primary_key=True),
        sa.Column("auto_search_id", sa.String(), nullable=False),
        sa.Column("departure_date", sa.DateTime(), nullable=False),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column("is_lowest_price", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["auto_search_id"], ["auto_search.auto_search_id"]),
    )
    op.create_index(
        "ix_auto_search_route_id", "auto_search", ["route_id"], unique=False
    )
    op.create_index(
        "ix_auto_search_airline_id", "auto_search", ["airline_id"], unique=False
    )
    op.create_index(
        "ix_price_auto_search_id", "price", ["auto_search_id"], unique=False
    )

def downgrade():
    op.drop_index("ix_price_auto_search_id", table_name="price")
    op.drop_table("price")
    op.drop_index("ix_auto_search_route_id", table_name="auto_search")
    op.drop_index("ix_auto_search_airline_id", table_name="auto_search")
    op.drop_table("auto_search")

    op.create_table(
        "price",
        sa.Column("price_id", sa.String(), primary_key=True),
        sa.Column("route_id", sa.String(), nullable=False),
        sa.Column("airline_id", sa.String(), nullable=False),
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
        sa.ForeignKeyConstraint(["route_id"], ["flight_route.route_id"]),
        sa.ForeignKeyConstraint(["airline_id"], ["airline.airline_id"]),
    )
    op.create_index("ix_price_route_id", "price", ["route_id"], unique=False)
    op.create_index("ix_price_airline_id", "price", ["airline_id"], unique=False)

