"""Run schema tweaks that create_all() can't express. New tables are created
automatically from models on startup — they don't need an entry here.

This file also drops the demo `items` table from the old boilerplate once.
"""

from sqlalchemy.ext.asyncio import AsyncEngine

from database.migration_helpers import add_column, create_index, execute_sql  # noqa: F401


async def run_migrations(engine: AsyncEngine) -> None:
    # Demo Item CRUD is gone — drop leftover table from earlier local/prod deploys.
    # IF EXISTS keeps this safe to re-run on every startup.
    await execute_sql(engine, "DROP TABLE IF EXISTS public.items CASCADE")
