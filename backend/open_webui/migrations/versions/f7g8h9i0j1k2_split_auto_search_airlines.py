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
    inspector = sa.inspect(bind)

    op.execute("DROP TABLE IF EXISTS _alembic_tmp_auto_search")

    # Check if auto_search table exists
    existing_tables = inspector.get_table_names()
    if "auto_search" not in existing_tables:
        # Table doesn't exist, skip this migration
        return

    auto_search_table = sa.Table(
        "auto_search",
        metadata,
        autoload_with=bind,
        extend_existing=True,
    )

    # Check if auto_search_airline table already exists
    if "auto_search_airline" not in existing_tables:
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
    
    # Check if indexes exist before creating them (only if table exists)
    existing_indexes = set()
    if "auto_search_airline" in existing_tables:
        try:
            existing_indexes = {idx["name"] for idx in inspector.get_indexes("auto_search_airline")}
        except Exception:
            # Table might exist but not be accessible, skip index check
            pass
    
    if "auto_search_airline" in existing_tables:
        if "ix_auto_search_airline_auto_search_id" not in existing_indexes:
            op.create_index(
                "ix_auto_search_airline_auto_search_id",
                "auto_search_airline",
                ["auto_search_id"],
                unique=False,
            )
        
        if "ix_auto_search_airline_airline_id" not in existing_indexes:
            op.create_index(
                "ix_auto_search_airline_airline_id",
                "auto_search_airline",
                ["airline_id"],
                unique=False,
            )

    # Only migrate data if auto_search_airline table exists and auto_search table has airline_id column
    auto_search_airline_table = None
    if "auto_search_airline" in existing_tables:
        try:
            auto_search_airline_table = sa.Table(
                "auto_search_airline", metadata, autoload_with=bind
            )
        except Exception:
            # Table structure might be incompatible, skip data migration
            auto_search_airline_table = None

    # Check if auto_search has airline_id column before migrating data
    column_names = {col["name"] for col in inspector.get_columns("auto_search")}
    if "airline_id" in column_names and auto_search_airline_table is not None:
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
    
    # Refresh column info after potential data migration
    column_names = {col["name"] for col in inspector.get_columns("auto_search")}
    index_names = {idx["name"] for idx in inspector.get_indexes("auto_search")}
    fk_names = {
        fk["name"]
        for fk in inspector.get_foreign_keys("auto_search")
        if fk.get("name")
    }

    # Check if we're using SQLite (which has issues with batch_alter_table when columns have unknown types)
    is_sqlite = bind.dialect.name == "sqlite"
    
    if is_sqlite:
        # For SQLite, use raw SQL to drop column to avoid autoload issues with NullType columns
        # SQLite doesn't support DROP COLUMN directly, so we need to recreate the table
        if "airline_id" in column_names:
            # Get all columns except airline_id
            all_columns = inspector.get_columns("auto_search")
            select_cols = [col["name"] for col in all_columns if col["name"] != "airline_id"]
            select_sql = ", ".join(select_cols)
            
            # Create new table without airline_id
            op.execute(f"""
                CREATE TABLE _alembic_tmp_auto_search_new AS 
                SELECT {select_sql}
                FROM auto_search
            """)
            
            # Drop old table
            op.execute("DROP TABLE auto_search")
            
            # Rename new table
            op.execute("ALTER TABLE _alembic_tmp_auto_search_new RENAME TO auto_search")
            
            # Recreate indexes that might have been dropped
            if "ix_auto_search_departure_route_id" not in index_names:
                op.execute("CREATE INDEX IF NOT EXISTS ix_auto_search_departure_route_id ON auto_search(departure_route_id)")
            if "ix_auto_search_return_route_id" not in index_names:
                op.execute("CREATE INDEX IF NOT EXISTS ix_auto_search_return_route_id ON auto_search(return_route_id)")
    else:
        # For other databases, use batch_alter_table
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

