"""Add flight search tables (searches, flight_options, flight_segments, etc.)

Revision ID: l5m6n7o8p9q0
Revises: k9l0m1n2o3p4
Create Date: 2025-12-10 20:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "l5m6n7o8p9q0"
down_revision = "k9l0m1n2o3p4"
branch_labels = None
depends_on = None


def upgrade():
    # Check if tables exist before creating (they may have been manually created)
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()
    
    # Create airline_auto table first (referenced by flight_segments)
    if "airline_auto" not in existing_tables:
        op.create_table(
            "airline_auto",
        sa.Column("airline_id", sa.VARCHAR(), primary_key=True),
        sa.Column("code", sa.VARCHAR(10), nullable=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("airline_logo", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("idx_airline_auto_code", "airline_auto", ["code"])

    # Create airport_auto table (referenced by flight_segments, layovers, search_airports)
    if "airport_auto" not in existing_tables:
        op.create_table(
            "airport_auto",
        sa.Column("airport_id", sa.VARCHAR(), primary_key=True),
        sa.Column("iata", sa.VARCHAR(), nullable=False, unique=True),
        sa.Column("airport_name", sa.Text(), nullable=False),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("country", sa.String(), nullable=True),
        sa.Column("country_code", sa.VARCHAR(2), nullable=True),
        sa.Column("image_url", sa.String(), nullable=True),
        sa.Column("thumbnail_url", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("idx_airport_auto_iata", "airport_auto", ["iata"])

    # Create searches table
    if "searches" not in existing_tables:
        op.create_table(
            "searches",
        sa.Column("search_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("engine", sa.String(), nullable=False),
        sa.Column("departure_id", sa.String(), nullable=False),
        sa.Column("arrival_id", sa.String(), nullable=False),
        sa.Column("currency", sa.String(), nullable=False),
        sa.Column("hl", sa.String(), nullable=True),
        sa.Column("gl", sa.String(), nullable=True),
        sa.Column("outbound_date", sa.Date(), nullable=False),
        sa.Column("return_date", sa.Date(), nullable=True),
        sa.Column("flight_type", sa.String(), nullable=False),
        sa.Column("travel_class", sa.String(), nullable=False),
        sa.Column("stops", sa.String(), nullable=True),
        sa.Column("adults", sa.Integer(), default=1),
        sa.Column("children", sa.Integer(), default=0),
        sa.Column("infants_in_seat", sa.Integer(), default=0),
        sa.Column("infants_on_lap", sa.Integer(), default=0),
        sa.Column("included_airlines", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("idx_searches_departure_arrival", "searches", ["departure_id", "arrival_id"])
        op.create_index("idx_searches_dates", "searches", ["outbound_date", "return_date"])

    # Create flight_options table
    if "flight_options" not in existing_tables:
        op.create_table(
            "flight_options",
        sa.Column("option_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("search_id", sa.Integer(), nullable=False),
        sa.Column("is_best_flight", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("total_duration", sa.Integer(), nullable=True),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(), nullable=True),
        sa.Column("airline_logo", sa.String(), nullable=True),
        sa.Column("departure_token", sa.String(), nullable=True),
        sa.Column("carbon_emission_this_flight", sa.Integer(), nullable=True),
        sa.Column("carbon_emission_typical", sa.Integer(), nullable=True),
        sa.Column("carbon_emission_difference_percent", sa.Float(), nullable=True),
        sa.Column("carbon_emission_lowest_route", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["search_id"], ["searches.search_id"], ondelete="CASCADE"),
        )
        op.create_index("idx_flight_options_search", "flight_options", ["search_id"])
        op.create_index("idx_flight_options_price", "flight_options", ["price"])

    # Create flight_segments table
    if "flight_segments" not in existing_tables:
        op.create_table(
            "flight_segments",
        sa.Column("segment_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("option_id", sa.Integer(), nullable=False),
        sa.Column("segment_order", sa.Integer(), nullable=False),
        sa.Column("departure_airport_iata", sa.VARCHAR(), nullable=False),
        sa.Column("departure_airport_name", sa.Text(), nullable=False),
        sa.Column("departure_date", sa.Date(), nullable=False),
        sa.Column("departure_time", sa.Time(), nullable=False),
        sa.Column("arrival_airport_iata", sa.VARCHAR(), nullable=False),
        sa.Column("arrival_airport_name", sa.Text(), nullable=False),
        sa.Column("arrival_date", sa.Date(), nullable=False),
        sa.Column("arrival_time", sa.Time(), nullable=False),
        sa.Column("duration", sa.Integer(), nullable=False),
        sa.Column("airplane", sa.String(), nullable=True),
        sa.Column("airline_id", sa.VARCHAR(), nullable=True),
        sa.Column("airline", sa.String(), nullable=True),
        sa.Column("airline_logo", sa.String(), nullable=True),
        sa.Column("travel_class", sa.String(), nullable=True),
        sa.Column("flight_number", sa.String(), nullable=False),
        sa.Column("is_overnight", sa.Boolean(), server_default=sa.text("0")),
        sa.Column("has_in_seat_usb_outlet", sa.Boolean(), nullable=True),
        sa.Column("has_power_and_usb_outlets", sa.Boolean(), nullable=True),
        sa.Column("has_on_demand_video", sa.Boolean(), nullable=True),
        sa.Column("wifi", sa.String(), nullable=True),
        sa.Column("seat_type", sa.String(), nullable=True),
        sa.Column("legroom_short", sa.String(), nullable=True),
        sa.Column("legroom_long", sa.String(), nullable=True),
        sa.Column("carbon_emission", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["option_id"], ["flight_options.option_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["departure_airport_iata"], ["airport_auto.iata"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["arrival_airport_iata"], ["airport_auto.iata"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["airline_id"], ["airline_auto.airline_id"], ondelete="SET NULL"),
        )
        op.create_index("idx_flight_segments_option", "flight_segments", ["option_id"])
        op.create_index("idx_flight_segments_airports", "flight_segments", ["departure_airport_iata", "arrival_airport_iata"])
        op.create_index("idx_flight_segments_airline", "flight_segments", ["airline_id"])
        op.create_index("idx_flight_segments_dates", "flight_segments", ["departure_date", "arrival_date"])

    # Create flight_extensions table
    if "flight_extensions" not in existing_tables:
        op.create_table(
            "flight_extensions",
        sa.Column("extension_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("segment_id", sa.Integer(), nullable=False),
        sa.Column("extension_text", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["segment_id"], ["flight_segments.segment_id"], ondelete="CASCADE"),
        )

    # Create option_extensions table
    if "option_extensions" not in existing_tables:
        op.create_table(
            "option_extensions",
        sa.Column("extension_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("option_id", sa.Integer(), nullable=False),
        sa.Column("extension_text", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["option_id"], ["flight_options.option_id"], ondelete="CASCADE"),
        )

    # Create layovers table
    if "layovers" not in existing_tables:
        op.create_table(
            "layovers",
        sa.Column("layover_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("option_id", sa.Integer(), nullable=False),
        sa.Column("layover_order", sa.Integer(), nullable=False),
        sa.Column("airport_iata", sa.VARCHAR(), nullable=False),
        sa.Column("airport_name", sa.String(), nullable=False),
        sa.Column("duration", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["option_id"], ["flight_options.option_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["airport_iata"], ["airport_auto.iata"], ondelete="RESTRICT"),
        )
        op.create_index("idx_layovers_option", "layovers", ["option_id"])

    # Create price_insights table
    if "price_insights" not in existing_tables:
        op.create_table(
            "price_insights",
        sa.Column("insight_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("search_id", sa.Integer(), nullable=False, unique=True),
        sa.Column("lowest_price", sa.Integer(), nullable=True),
        sa.Column("price_level", sa.String(), nullable=True),
        sa.Column("typical_low_price", sa.Integer(), nullable=True),
        sa.Column("typical_high_price", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["search_id"], ["searches.search_id"], ondelete="CASCADE"),
        )

    # Create price_history table
    if "price_history" not in existing_tables:
        op.create_table(
            "price_history",
        sa.Column("history_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("insight_id", sa.Integer(), nullable=False),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column("iso_date", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["insight_id"], ["price_insights.insight_id"], ondelete="CASCADE"),
        )
        op.create_index("idx_price_history_insight", "price_history", ["insight_id"])
        op.create_index("idx_price_history_date", "price_history", ["iso_date"])

    # Create search_airports table
    if "search_airports" not in existing_tables:
        op.create_table(
            "search_airports",
        sa.Column("search_airport_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("search_id", sa.Integer(), nullable=False),
        sa.Column("airport_iata", sa.VARCHAR(), nullable=False),
        sa.Column("is_departure", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["search_id"], ["searches.search_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["airport_iata"], ["airport_auto.iata"], ondelete="RESTRICT"),
        )
        op.create_index("idx_search_airports_search", "search_airports", ["search_id"])
        op.create_index("idx_search_airports_airport", "search_airports", ["airport_iata"])


def downgrade():
    op.drop_index("idx_search_airports_airport", "search_airports")
    op.drop_index("idx_search_airports_search", "search_airports")
    op.drop_table("search_airports")
    op.drop_index("idx_price_history_date", "price_history")
    op.drop_index("idx_price_history_insight", "price_history")
    op.drop_table("price_history")
    op.drop_table("price_insights")
    op.drop_index("idx_layovers_option", "layovers")
    op.drop_table("layovers")
    op.drop_table("option_extensions")
    op.drop_table("flight_extensions")
    op.drop_index("idx_flight_segments_dates", "flight_segments")
    op.drop_index("idx_flight_segments_airline", "flight_segments")
    op.drop_index("idx_flight_segments_airports", "flight_segments")
    op.drop_index("idx_flight_segments_option", "flight_segments")
    op.drop_table("flight_segments")
    op.drop_index("idx_flight_options_price", "flight_options")
    op.drop_index("idx_flight_options_search", "flight_options")
    op.drop_table("flight_options")
    op.drop_index("idx_searches_dates", "searches")
    op.drop_index("idx_searches_departure_arrival", "searches")
    op.drop_table("searches")
    op.drop_index("idx_airport_auto_iata", "airport_auto")
    op.drop_table("airport_auto")
    op.drop_index("idx_airline_auto_code", "airline_auto")
    op.drop_table("airline_auto")

