"""Link flight routes to airport IDs

Revision ID: j2k3l4m5n6o7
Revises: i3j4k5l6m7n8
Create Date: 2025-01-15 18:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "j2k3l4m5n6o7"
down_revision = "i3j4k5l6m7n8"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    column_names = {col["name"] for col in inspector.get_columns("flight_route")}

    with op.batch_alter_table("flight_route", recreate="always") as batch:
        if "flight_route_from_place_fkey" in {
            fk["name"] for fk in inspector.get_foreign_keys("flight_route")
        }:
            batch.drop_constraint(
                "flight_route_from_place_fkey", type_="foreignkey"
            )
        if "flight_route_to_place_fkey" in {
            fk["name"] for fk in inspector.get_foreign_keys("flight_route")
        }:
            batch.drop_constraint("flight_route_to_place_fkey", type_="foreignkey")

        if "from_place" in column_names:
            batch.drop_column("from_place")
        if "to_place" in column_names:
            batch.drop_column("to_place")

        batch.add_column(
            sa.Column("from_airport_id", sa.String(), nullable=False, index=True)
        )
        batch.add_column(
            sa.Column("to_airport_id", sa.String(), nullable=False, index=True)
        )
        batch.create_foreign_key(
            "flight_route_from_airport_id_fkey",
            "airport",
            ["from_airport_id"],
            ["airport_id"],
            ondelete="CASCADE",
        )
        batch.create_foreign_key(
            "flight_route_to_airport_id_fkey",
            "airport",
            ["to_airport_id"],
            ["airport_id"],
            ondelete="CASCADE",
        )
        batch.create_index(
            "ix_flight_route_from_airport_id",
            ["from_airport_id"],
            unique=False,
        )
        batch.create_index(
            "ix_flight_route_to_airport_id",
            ["to_airport_id"],
            unique=False,
        )


def downgrade():
    with op.batch_alter_table("flight_route", recreate="always") as batch:
        batch.drop_constraint(
            "flight_route_to_airport_id_fkey", type_="foreignkey"
        )
        batch.drop_constraint(
            "flight_route_from_airport_id_fkey", type_="foreignkey"
        )
        batch.drop_index("ix_flight_route_to_airport_id")
        batch.drop_index("ix_flight_route_from_airport_id")
        batch.drop_column("to_airport_id")
        batch.drop_column("from_airport_id")
        batch.add_column(
            sa.Column("to_place", sa.String(length=10), nullable=False)
        )
        batch.add_column(
            sa.Column("from_place", sa.String(length=10), nullable=False)
        )

