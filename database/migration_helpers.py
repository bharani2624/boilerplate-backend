"""Idempotent schema-migration helpers. New tables don't need these — SQLModel's
create_all (see database/session.py) creates them automatically on startup.
Use these only for altering columns on tables that already exist in production.
"""

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import ProgrammingError


def add_column(
    engine: Engine,
    table_name: str,
    column_name: str,
    column_type: str,
    nullable: bool = True,
    default_value: str = None,
    schema: str = "public",
):
    full_table_name = f"{schema}.{table_name}"
    check_sql = """
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = :schema AND table_name = :table AND column_name = :column
    """
    with engine.connect() as conn:
        exists = conn.execute(
            text(check_sql), {"schema": schema, "table": table_name, "column": column_name}
        ).fetchone()
        if exists:
            return

        alter_sql = f"ALTER TABLE {full_table_name} ADD COLUMN {column_name} {column_type}"
        if not nullable:
            alter_sql += " NOT NULL"
        if default_value is not None:
            alter_sql += f" DEFAULT {default_value}"

        try:
            conn.execute(text(alter_sql))
            conn.commit()
        except ProgrammingError as e:
            if getattr(e.orig, "pgcode", None) == "42701":  # duplicate_column
                conn.rollback()
            else:
                raise


def drop_column(engine: Engine, table_name: str, column_name: str, schema: str = "public"):
    full_table_name = f"{schema}.{table_name}"
    check_sql = """
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = :schema AND table_name = :table AND column_name = :column
    """
    with engine.connect() as conn:
        exists = conn.execute(
            text(check_sql), {"schema": schema, "table": table_name, "column": column_name}
        ).fetchone()
        if exists:
            conn.execute(text(f"ALTER TABLE {full_table_name} DROP COLUMN {column_name}"))
            conn.commit()


def create_index(
    engine: Engine,
    table_name: str,
    column_names: list[str],
    index_name: str = None,
    unique: bool = False,
    schema: str = "public",
):
    full_table_name = f"{schema}.{table_name}"
    index_name = index_name or f"idx_{table_name}_{'_'.join(column_names)}"
    check_sql = """
        SELECT indexname FROM pg_indexes
        WHERE schemaname = :schema AND tablename = :table AND indexname = :index
    """
    with engine.connect() as conn:
        exists = conn.execute(
            text(check_sql), {"schema": schema, "table": table_name, "index": index_name}
        ).fetchone()
        if exists:
            return
        unique_str = "UNIQUE " if unique else ""
        columns_str = ", ".join(column_names)
        conn.execute(text(f"CREATE {unique_str}INDEX {index_name} ON {full_table_name} ({columns_str})"))
        conn.commit()


def execute_sql(engine: Engine, sql: str):
    with engine.connect() as conn:
        conn.execute(text(sql))
        conn.commit()
