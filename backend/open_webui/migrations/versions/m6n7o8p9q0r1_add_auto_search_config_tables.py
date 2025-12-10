"""Add auto search config tables (auto_search_config, auto_search_airline)

Revision ID: m6n7o8p9q0r1
Revises: l5m6n7o8p9q0
Create Date: 2025-12-10 21:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "m6n7o8p9q0r1"
down_revision = "l5m6n7o8p9q0"
branch_labels = None
depends_on = None


def upgrade():
    # Check if tables exist before creating (they may have been manually created)
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()
    
    # Create auto_search_config table
    if "auto_search_config" not in existing_tables:
        op.create_table(
            "auto_search_config",
            sa.Column("auto_search_id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("departure_id", sa.String(), nullable=False),
            sa.Column("arrival_id", sa.String(), nullable=False),
            sa.Column("travel_class", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("is_direct", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("return_trip_duration", sa.Integer(), nullable=False, server_default=sa.text("7")),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
        op.create_index("idx_auto_search_config_route", "auto_search_config", ["departure_id", "arrival_id"])

    # Create auto_search_airline table (junction table)
    if "auto_search_airline" not in existing_tables:
        op.create_table(
            "auto_search_airline",
            sa.Column("auto_search_airline_id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("auto_search_id", sa.Integer(), nullable=False),
            sa.Column("airline_id", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["auto_search_id"], ["auto_search_config.auto_search_id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["airline_id"], ["airline.airline_id"], ondelete="CASCADE"),
            sa.UniqueConstraint("auto_search_id", "airline_id", name="uq_auto_search_airline"),
        )
        op.create_index("idx_auto_search_airline_search", "auto_search_airline", ["auto_search_id"])
        op.create_index("idx_auto_search_airline_airline", "auto_search_airline", ["airline_id"])

    # Add auto_search_airline_id column to searches table if it doesn't exist
    # SQLite requires batch mode for ALTER operations
    if "searches" in existing_tables:
        columns = {col["name"] for col in inspector.get_columns("searches")}
        if "auto_search_airline_id" not in columns:
            # Use batch mode for SQLite compatibility
            with op.batch_alter_table("searches", schema=None) as batch_op:
                batch_op.add_column(
                    sa.Column("auto_search_airline_id", sa.Integer(), nullable=True)
                )
                batch_op.create_foreign_key(
                    "fk_searches_auto_search_airline",
                    "auto_search_airline",
                    ["auto_search_airline_id"],
                    ["auto_search_airline_id"],
                    ondelete="SET NULL"
                )
                batch_op.create_index("idx_searches_auto_search_airline", ["auto_search_airline_id"])


def downgrade():
    # Remove auto_search_airline_id from searches table
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "searches" in inspector.get_table_names():
        columns = {col["name"] for col in inspector.get_columns("searches")}
        if "auto_search_airline_id" in columns:
            op.drop_index("idx_searches_auto_search_airline", "searches")
            op.drop_constraint("fk_searches_auto_search_airline", "searches", type_="foreignkey")
            op.drop_column("searches", "auto_search_airline_id")
    
    # Drop auto_search_airline table
    if "auto_search_airline" in inspector.get_table_names():
        op.drop_index("idx_auto_search_airline_airline", "auto_search_airline")
        op.drop_index("idx_auto_search_airline_search", "auto_search_airline")
        op.drop_table("auto_search_airline")
    
    # Drop auto_search_config table
    if "auto_search_config" in inspector.get_table_names():
        op.drop_index("idx_auto_search_config_route", "auto_search_config")
        op.drop_table("auto_search_config")

