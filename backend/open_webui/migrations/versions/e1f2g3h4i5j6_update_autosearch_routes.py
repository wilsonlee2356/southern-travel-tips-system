"""Update auto_search route references

Revision ID: e1f2g3h4i5j6
Revises: d7e8f9g0h1i2
Create Date: 2025-11-12 19:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "e1f2g3h4i5j6"
down_revision = "d7e8f9g0h1i2"
branch_labels = None
depends_on = None


def upgrade():
    # clean up any leftover temp tables from prior failed runs
    op.execute("DROP TABLE IF EXISTS _alembic_tmp_auto_search")

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    column_names = {col["name"] for col in inspector.get_columns("auto_search")}
    fk_names = {fk["name"] for fk in inspector.get_foreign_keys("auto_search") if fk.get("name")}
    index_names = {idx["name"] for idx in inspector.get_indexes("auto_search")}

    with op.batch_alter_table("auto_search", recreate="always") as batch_op:
        if "auto_search_route_id_fkey" in fk_names:
            batch_op.drop_constraint("auto_search_route_id_fkey", type_="foreignkey")
        if "ix_auto_search_route_id" in index_names:
            batch_op.drop_index("ix_auto_search_route_id")
        if "route_id" in column_names:
            batch_op.alter_column("route_id", new_column_name="departure_route_id")
        if "return_route_id" not in column_names:
            batch_op.add_column(sa.Column("return_route_id", sa.String(), nullable=True))

        batch_op.create_index(
            "ix_auto_search_departure_route_id",
            ["departure_route_id"],
            unique=False,
        )
        batch_op.create_index(
            "ix_auto_search_return_route_id",
            ["return_route_id"],
            unique=False,
        )
        batch_op.create_foreign_key(
            "auto_search_departure_route_id_fkey",
            "flight_route",
            ["departure_route_id"],
            ["route_id"],
        )
        batch_op.create_foreign_key(
            "auto_search_return_route_id_fkey",
            "flight_route",
            ["return_route_id"],
            ["route_id"],
        )


def downgrade():
    op.execute("DROP TABLE IF EXISTS _alembic_tmp_auto_search")

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    fk_names = {fk["name"] for fk in inspector.get_foreign_keys("auto_search") if fk.get("name")}
    index_names = {idx["name"] for idx in inspector.get_indexes("auto_search")}
    column_names = {col["name"] for col in inspector.get_columns("auto_search")}

    with op.batch_alter_table("auto_search", recreate="always") as batch_op:
        if "auto_search_return_route_id_fkey" in fk_names:
            batch_op.drop_constraint(
                "auto_search_return_route_id_fkey",
                type_="foreignkey",
            )
        if "auto_search_departure_route_id_fkey" in fk_names:
            batch_op.drop_constraint(
                "auto_search_departure_route_id_fkey",
                type_="foreignkey",
            )
        if "ix_auto_search_return_route_id" in index_names:
            batch_op.drop_index("ix_auto_search_return_route_id")
        if "ix_auto_search_departure_route_id" in index_names:
            batch_op.drop_index("ix_auto_search_departure_route_id")
        if "return_route_id" in column_names:
            batch_op.drop_column("return_route_id")
        if "departure_route_id" in column_names:
            batch_op.alter_column("departure_route_id", new_column_name="route_id")
        batch_op.create_index("ix_auto_search_route_id", ["route_id"], unique=False)
        batch_op.create_foreign_key(
            "auto_search_route_id_fkey",
            "flight_route",
            ["route_id"],
            ["route_id"],
        )

