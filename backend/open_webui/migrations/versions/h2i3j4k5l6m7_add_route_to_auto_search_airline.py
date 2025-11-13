"""add route to auto_search_airline

Revision ID: h2i3j4k5l6m7
Revises: g4h5i6j7k8l9
Create Date: 2025-11-13 19:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "h2i3j4k5l6m7"
down_revision = "g4h5i6j7k8l9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    existing_columns = {col["name"] for col in inspector.get_columns("auto_search_airline")}
    if "route_id" not in existing_columns:
        op.add_column(
            "auto_search_airline",
            sa.Column("route_id", sa.String(), nullable=True),
        )

    op.execute(
        """
        UPDATE auto_search_airline
        SET route_id = (
            SELECT departure_route_id
            FROM auto_search
            WHERE auto_search.auto_search_id = auto_search_airline.auto_search_id
        )
        WHERE route_id IS NULL
        """
    )

    with op.batch_alter_table("auto_search_airline", recreate="always") as batch:
        batch.drop_constraint("uq_auto_search_airline_pair", type_="unique")
        batch.alter_column("route_id", existing_type=sa.String(), nullable=False)
        batch.create_unique_constraint(
            "uq_auto_search_airline_triplet",
            ["auto_search_id", "airline_id", "route_id"],
        )
        batch.create_index(
            "ix_auto_search_airline_route_id", ["route_id"], unique=False
        )
        batch.create_foreign_key(
            "fk_auto_search_airline_route_id",
            "flight_route",
            ["route_id"],
            ["route_id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    with op.batch_alter_table("auto_search_airline", recreate="always") as batch:
        batch.drop_constraint("fk_auto_search_airline_route_id", type_="foreignkey")
        batch.drop_index("ix_auto_search_airline_route_id")
        batch.drop_constraint("uq_auto_search_airline_triplet", type_="unique")
        batch.create_unique_constraint(
            "uq_auto_search_airline_pair", ["auto_search_id", "airline_id"]
        )
        batch.drop_column("route_id")

