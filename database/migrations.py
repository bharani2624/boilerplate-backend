"""Run schema tweaks that create_all() can't express (column adds/drops/renames on
existing tables). New tables are created automatically from models on startup —
they don't need an entry here. Add new migrations at the bottom; each helper call
is idempotent, safe to re-run.

Why this file exists: it's called once from the FastAPI lifespan in src/api/app.py on
every startup, so any column you add here rolls out automatically on next deploy —
no separate migration-running step to remember or forget.
"""

from sqlalchemy.ext.asyncio import AsyncEngine

from database.migration_helpers import add_column, create_index  # noqa: F401


async def run_migrations(engine: AsyncEngine) -> None:
    # Example (uncomment / copy when you add a column to an existing table):
    # await add_column(engine, "items", "priority", "integer", default_value="0")
    pass
