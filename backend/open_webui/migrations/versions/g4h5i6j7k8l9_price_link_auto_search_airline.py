"""link price to auto_search_airline

Revision ID: g4h5i6j7k8l9
Revises: f7g8h9i0j1k2
Create Date: 2025-11-13 18:05:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "g4h5i6j7k8l9"
down_revision = "f7g8h9i0j1k2"
branch_labels = None
depends_on = None


def _column_exists(inspector, table_name: str, column_name: str) -> bool:
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def _index_exists(inspector, table_name: str, index_name: str) -> bool:
    return any(idx["name"] == index_name for idx in inspector.get_indexes(table_name))


def _fk_exists(inspector, table_name: str, fk_name: str) -> bool:
    return any(fk["name"] == fk_name for fk in inspector.get_foreign_keys(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    has_auto_search_airline_col = _column_exists(
        inspector, "price", "auto_search_airline_id"
    )

    if not has_auto_search_airline_col:
        with op.batch_alter_table("price", recreate="always") as batch:
            batch.add_column(
                sa.Column("auto_search_airline_id", sa.String(), nullable=True)
            )

    op.execute(
        """
        UPDATE price
        SET auto_search_airline_id = (
            SELECT asa.auto_search_airline_id
            FROM auto_search_airline asa
            WHERE asa.auto_search_id = price.auto_search_id
            ORDER BY asa.created_at ASC
            LIMIT 1
        )
        WHERE auto_search_id IS NOT NULL AND auto_search_airline_id IS NULL
        """
    )

    op.execute("DELETE FROM price WHERE auto_search_airline_id IS NULL")

    inspector = sa.inspect(bind)

    fk_to_auto_search = next(
        (
            fk["name"]
            for fk in inspector.get_foreign_keys("price")
            if fk["referred_table"] == "auto_search"
        ),
        None,
    )
    has_auto_search_id = _column_exists(inspector, "price", "auto_search_id")
    has_old_index = _index_exists(inspector, "price", "ix_price_auto_search_id")
    has_new_index = _index_exists(
        inspector, "price", "ix_price_auto_search_airline_id"
    )
    has_new_fk = _fk_exists(inspector, "price", "fk_price_auto_search_airline_id")

    with op.batch_alter_table("price", recreate="always") as batch:
        if has_old_index:
            batch.drop_index("ix_price_auto_search_id")
        if fk_to_auto_search:
            batch.drop_constraint(fk_to_auto_search, type_="foreignkey")
        batch.alter_column(
            "auto_search_airline_id",
            existing_type=sa.String(),
            nullable=False,
        )
        if has_auto_search_id:
            batch.drop_column("auto_search_id")
        if not has_new_index:
            batch.create_index(
                "ix_price_auto_search_airline_id", ["auto_search_airline_id"]
            )
        if not has_new_fk:
            batch.create_foreign_key(
                "fk_price_auto_search_airline_id",
                "auto_search_airline",
                ["auto_search_airline_id"],
                ["auto_search_airline_id"],
                ondelete="CASCADE",
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    has_auto_search_id = _column_exists(inspector, "price", "auto_search_id")

    if not has_auto_search_id:
        with op.batch_alter_table("price", recreate="always") as batch:
            batch.add_column(sa.Column("auto_search_id", sa.String(), nullable=True))

    op.execute(
        """
        UPDATE price
        SET auto_search_id = (
            SELECT asa.auto_search_id
            FROM auto_search_airline asa
            WHERE asa.auto_search_airline_id = price.auto_search_airline_id
        )
        WHERE auto_search_id IS NULL
        """
    )

    inspector = sa.inspect(bind)

    has_new_index = _index_exists(inspector, "price", "ix_price_auto_search_airline_id")
    has_old_index = _index_exists(inspector, "price", "ix_price_auto_search_id")
    has_new_fk = _fk_exists(inspector, "price", "fk_price_auto_search_airline_id")
    has_old_fk = _fk_exists(inspector, "price", "fk_price_auto_search_id")

    with op.batch_alter_table("price", recreate="always") as batch:
        if has_new_fk:
            batch.drop_constraint("fk_price_auto_search_airline_id", type_="foreignkey")
        if has_new_index:
            batch.drop_index("ix_price_auto_search_airline_id")
        batch.alter_column("auto_search_id", existing_type=sa.String(), nullable=False)
        if not has_old_index:
            batch.create_index("ix_price_auto_search_id", ["auto_search_id"])
        if not has_old_fk:
            batch.create_foreign_key(
                "fk_price_auto_search_id",
                "auto_search",
                ["auto_search_id"],
                ["auto_search_id"],
                ondelete="CASCADE",
            )
        batch.drop_column("auto_search_airline_id")

