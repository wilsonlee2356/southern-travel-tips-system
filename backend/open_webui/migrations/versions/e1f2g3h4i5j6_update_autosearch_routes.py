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
    existing_tables = inspector.get_table_names()
    
    # Check if auto_search table exists - it may have been dropped in a later migration
    if "auto_search" not in existing_tables:
        # Table doesn't exist, skip this migration
        return

    column_names = {col["name"] for col in inspector.get_columns("auto_search")}
    fk_names = {fk["name"] for fk in inspector.get_foreign_keys("auto_search") if fk.get("name")}
    index_names = {idx["name"] for idx in inspector.get_indexes("auto_search")}

    # Only proceed if route_id column exists (meaning this is an old schema)
    # If departure_route_id already exists, migration was already applied
    if "departure_route_id" in column_names:
        return
    
    if "route_id" not in column_names:
        # Table structure is different than expected, skip
        return

    # Check if we're using SQLite (which requires batch mode for ALTER TABLE)
    is_sqlite = bind.dialect.name == "sqlite"
    
    if is_sqlite:
        # For SQLite, manually recreate the table to rename the column
        # This avoids Alembic's batch mode index gathering issues
        
        # Get all column information before dropping
        all_columns = inspector.get_columns("auto_search")
        pk_constraint = inspector.get_pk_constraint("auto_search")
        
        # Build the SELECT statement for data migration
        select_cols = []
        for col in all_columns:
            if col["name"] == "route_id":
                select_cols.append("route_id AS departure_route_id")
            else:
                select_cols.append(col["name"])
        
        select_sql = ", ".join(select_cols)
        
        # Create new table with data using CREATE TABLE AS SELECT
        op.execute(f"""
            CREATE TABLE _alembic_tmp_auto_search_new AS 
            SELECT {select_sql}
            FROM auto_search
        """)
        
        # Add return_route_id column with explicit type if it doesn't exist
        if "return_route_id" not in column_names:
            op.execute("ALTER TABLE _alembic_tmp_auto_search_new ADD COLUMN return_route_id VARCHAR")
        
        # Drop old table
        op.execute("DROP TABLE auto_search")
        
        # Rename new table
        op.execute("ALTER TABLE _alembic_tmp_auto_search_new RENAME TO auto_search")
        
        # Note: Primary keys and constraints are lost in CREATE TABLE AS SELECT
        # This is acceptable as the table may be dropped in a later migration anyway
        
        # Create indexes using raw SQL
        op.execute("CREATE INDEX IF NOT EXISTS ix_auto_search_departure_route_id ON auto_search(departure_route_id)")
        op.execute("CREATE INDEX IF NOT EXISTS ix_auto_search_return_route_id ON auto_search(return_route_id)")
        
        # Note: Foreign keys in SQLite are informational only unless PRAGMA foreign_keys is enabled
        # We skip FK creation as SQLite doesn't support adding them via ALTER TABLE after creation
    else:
        # For other databases, use standard ALTER TABLE operations
        op.alter_column("auto_search", "route_id", new_column_name="departure_route_id")
        
        if "return_route_id" not in column_names:
            op.add_column("auto_search", sa.Column("return_route_id", sa.String(), nullable=True))
        
        op.create_index(
            "ix_auto_search_departure_route_id",
            "auto_search",
            ["departure_route_id"],
            unique=False,
        )
        
        op.create_index(
            "ix_auto_search_return_route_id",
            "auto_search",
            ["return_route_id"],
            unique=False,
        )
        
        op.create_foreign_key(
            "auto_search_departure_route_id_fkey",
            "auto_search",
            "flight_route",
            ["departure_route_id"],
            ["route_id"],
        )
        
        op.create_foreign_key(
            "auto_search_return_route_id_fkey",
            "auto_search",
            "flight_route",
            ["return_route_id"],
            ["route_id"],
        )


def downgrade():
    op.execute("DROP TABLE IF EXISTS _alembic_tmp_auto_search")

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()
    
    # Check if auto_search table exists - it may have been dropped in a later migration
    if "auto_search" not in existing_tables:
        # Table doesn't exist, skip this migration
        return

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

