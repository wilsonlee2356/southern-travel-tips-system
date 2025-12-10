"""Drop flight pricing tables (auto_search, auto_search_airline, flight_route, price)

Revision ID: k9l0m1n2o3p4
Revises: j2k3l4m5n6o7
Create Date: 2025-12-10 18:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "k9l0m1n2o3p4"
down_revision = "j2k3l4m5n6o7"
branch_labels = None
depends_on = None


def upgrade():
    # Drop tables in order to respect foreign key constraints
    # Check if tables exist before dropping (they may have been manually removed)
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()
    
    # Drop price table first (has FK to auto_search_airline)
    if "price" in existing_tables:
        op.drop_table("price")
    
    # Drop auto_search_airline table (has FK to auto_search and flight_route)
    if "auto_search_airline" in existing_tables:
        op.drop_table("auto_search_airline")
    
    # Drop auto_search table (has FK to flight_route)
    if "auto_search" in existing_tables:
        op.drop_table("auto_search")
    
    # Drop flight_route table (has FK to airport)
    if "flight_route" in existing_tables:
        op.drop_table("flight_route")


def downgrade():
    # Recreate tables in reverse order
    op.create_table(
        "flight_route",
        sa.Column("route_id", sa.String(), primary_key=True),
        sa.Column("from_airport_id", sa.String(), nullable=False, index=True),
        sa.Column("to_airport_id", sa.String(), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["from_airport_id"],
            ["airport.airport_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["to_airport_id"],
            ["airport.airport_id"],
            ondelete="CASCADE",
        ),
    )
    
    op.create_table(
        "auto_search",
        sa.Column("auto_search_id", sa.String(), primary_key=True),
        sa.Column("departure_route_id", sa.String(), nullable=False, index=True),
        sa.Column("return_route_id", sa.String(), nullable=True, index=True),
        sa.Column("travel_class", sa.Integer(), nullable=False, default=0),
        sa.Column("direct_flight", sa.Boolean(), nullable=False, default=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["departure_route_id"],
            ["flight_route.route_id"],
        ),
        sa.ForeignKeyConstraint(
            ["return_route_id"],
            ["flight_route.route_id"],
        ),
    )
    
    op.create_table(
        "auto_search_airline",
        sa.Column("auto_search_airline_id", sa.String(), primary_key=True),
        sa.Column("auto_search_id", sa.String(), nullable=False, index=True),
        sa.Column("airline_id", sa.String(), nullable=False, index=True),
        sa.Column("route_id", sa.String(), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["auto_search_id"],
            ["auto_search.auto_search_id"],
        ),
        sa.ForeignKeyConstraint(
            ["airline_id"],
            ["airline.airline_id"],
        ),
        sa.ForeignKeyConstraint(
            ["route_id"],
            ["flight_route.route_id"],
        ),
        sa.UniqueConstraint(
            "auto_search_id",
            "airline_id",
            "route_id",
            name="uq_auto_search_airline_triplet",
        ),
    )
    
    op.create_table(
        "price",
        sa.Column("price_id", sa.String(), primary_key=True),
        sa.Column("auto_search_airline_id", sa.String(), nullable=False, index=True),
        sa.Column("departure_date", sa.DateTime(), nullable=False),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column("is_lowest_price", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["auto_search_airline_id"],
            ["auto_search_airline.auto_search_airline_id"],
        ),
    )

