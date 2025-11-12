"""Split auto_search airlines into junction table

Revision ID: f7g8h9i0j1k2
Revises: e1f2g3h4i5j6
Create Date: 2025-11-12 20:45:00.000000
"""

from datetime import datetime
import uuid

from alembic import op
import sqlalchemy as sa


revision = "f7g8h9i0j1k2"
down_revision = "e1f2g3h4i5j6"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    metadata = sa.MetaData()

    op.execute("DROP TABLE IF EXISTS _alembic_tmp_auto_search")

    auto_search_table = sa.Table(
        "auto_search",
        metadata,
        autoload_with=bind,
        extend_existing=True,
    )

    op.create_table(
        "auto_search_airline",
        sa.Column("auto_search_airline_id", sa.String(), primary_key=True),
        sa.Column("auto_search_id", sa.String(), nullable=False),
        sa.Column("airline_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["auto_search_id"], ["auto_search.auto_search_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["airline_id"], ["airline.airline_id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "auto_search_id", "airline_id", name="uq_auto_search_airline_pair"
        ),
    )
    op.create_index(
        "ix_auto_search_airline_auto_search_id",
        "auto_search_airline",
        ["auto_search_id"],
        unique=False,
    )
    op.create_index(
        "ix_auto_search_airline_airline_id",
        "auto_search_airline",
        ["airline_id"],
        unique=False,
    )

    auto_search_airline_table = sa.Table(
        "auto_search_airline", metadata, autoload_with=bind
    )

    rows = list(bind.execute(sa.select(auto_search_table)))
    now = datetime.utcnow()
    inserts = []
    for row in rows:
        if not getattr(row, "airline_id", None):
            continue
        inserts.append(
            {
                "auto_search_airline_id": str(uuid.uuid4()),
                "auto_search_id": row.auto_search_id,
                "airline_id": row.airline_id,
                "created_at": row.created_at or now,
                "updated_at": row.updated_at or now,
            }
        )

    if inserts:
        bind.execute(auto_search_airline_table.insert(), inserts)

    inspector = sa.inspect(bind)
    column_names = {col["name"] for col in inspector.get_columns("auto_search")}
    index_names = {idx["name"] for idx in inspector.get_indexes("auto_search")}
    fk_names = {
        fk["name"]
        for fk in inspector.get_foreign_keys("auto_search")
        if fk.get("name")
    }

    with op.batch_alter_table("auto_search", recreate="always") as batch_op:
        if "auto_search_airline_id_fkey" in fk_names:
            batch_op.drop_constraint("auto_search_airline_id_fkey", type_="foreignkey")
        if "ix_auto_search_airline_id" in index_names:
            batch_op.drop_index("ix_auto_search_airline_id")
        if "airline_id" in column_names:
            batch_op.drop_column("airline_id")


def downgrade():
    bind = op.get_bind()
    metadata = sa.MetaData()

    op.execute("DROP TABLE IF EXISTS _alembic_tmp_auto_search")

    auto_search_table = sa.Table(
        "auto_search", metadata, autoload_with=bind, extend_existing=True
    )
    auto_search_airline_table = sa.Table(
        "auto_search_airline", metadata, autoload_with=bind
    )

    with op.batch_alter_table("auto_search", recreate="always") as batch_op:
        batch_op.add_column(sa.Column("airline_id", sa.String(), nullable=True))
        batch_op.create_index("ix_auto_search_airline_id", ["airline_id"], unique=False)
        batch_op.create_foreign_key(
            "auto_search_airline_id_fkey",
            "airline",
            ["airline_id"],
            ["airline_id"],
        )

    # Reload table definition with new column
    auto_search_table = sa.Table(
        "auto_search", metadata, autoload_with=bind, extend_existing=True
    )

    # Populate airline_id from junction table (first airline per auto_search)
    rows = list(
        bind.execute(
            sa.select(
                auto_search_airline_table.c.auto_search_id,
                auto_search_airline_table.c.airline_id,
            ).order_by(auto_search_airline_table.c.created_at.asc())
        )
    )
    seen = set()
    for row in rows:
        if row.auto_search_id in seen:
            continue
        seen.add(row.auto_search_id)
        bind.execute(
            auto_search_table.update()
            .where(auto_search_table.c.auto_search_id == row.auto_search_id)
            .values(airline_id=row.airline_id)
        )

    op.drop_index("ix_auto_search_airline_auto_search_id", table_name="auto_search_airline")
    op.drop_index("ix_auto_search_airline_airline_id", table_name="auto_search_airline")
    op.drop_table("auto_search_airline")

