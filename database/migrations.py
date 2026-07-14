"""Run schema tweaks that create_all() can't express (column adds/drops/renames on
existing tables). New tables are created automatically from models on startup —
they don't need an entry here. Add new migrations at the bottom; each helper call
is idempotent, safe to re-run.
"""

from sqlalchemy.engine import Engine

from database.migration_helpers import add_column, create_index  # noqa: F401


def run_migrations(engine: Engine) -> None:
    # Example (uncomment / copy when you add a column to an existing table):
    # add_column(engine, "items", "priority", "integer", default_value="0")
    pass
