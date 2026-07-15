"""Single shared async engine for the Supabase Postgres database.

Why this file exists: every store (src/store/*.py) needs a database session, and they
all need to share one connection pool rather than each opening its own. This module is
the one place that creates the SQLAlchemy `engine` and hands out sessions from it.

Async, not sync: psycopg3 (our driver, see requirements.txt) natively supports asyncio,
so every route and store in this project is `async def` and awaits its database calls —
that's what lets one worker process handle many concurrent requests without a query on
one request blocking another (see AGENTS.md's "Concurrency" section for the full
reasoning). `create_async_engine` + `AsyncSession` is the async equivalent of the
`create_engine` + `Session` pair you'd use in a sync app.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlmodel import SQLModel

from config.settings import settings

# Register every table model on SQLModel.metadata before create_all runs.
import database.models  # noqa: F401, E402

# pool_pre_ping=True: check a pooled connection is still alive before using it — Supabase's
# pooler (and most managed Postgres) will silently drop idle connections, and without this
# the first query after a lull would fail with "server closed the connection unexpectedly."
#
# prepare_threshold=None: disable psycopg3 prepared statements. Required for Supabase's
# transaction-mode pooler (port 6543 / PgBouncer). With prepared statements on, a later
# query can reuse a portal typed for a previous query — e.g. a UUID bind from a cart
# PK lookup bleeding into a promo-code TEXT lookup, which surfaces as:
#   invalid input syntax for type uuid: "SAVE10"
# even though promos.code is TEXT and the SQL text says WHERE code = ...
engine: AsyncEngine = create_async_engine(
    settings.database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_pre_ping=True,
    connect_args={"prepare_threshold": None},
)


async def create_db_and_tables() -> None:
    """Create tables that don't exist yet. Safe to call on every startup.

    Every SQLModel class with table=True that has been imported (see
    database/models/__init__.py) registers itself on SQLModel.metadata; create_all
    only issues CREATE TABLE for the ones that aren't already in the database, so this
    never touches tables that already exist. run_sync is needed because create_all
    itself is a synchronous SQLAlchemy call — this runs it against a sync-style proxy
    of our async connection, which is the standard way to use metadata operations with
    an async engine.
    """
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a session, commit on success, rollback on error, always close.

    Stores use this as `async with self.get_session() as session:` so none of them
    need to remember to commit/rollback/close themselves — one bug here is fixed
    everywhere.
    """
    # expire_on_commit=False: objects stay usable after the `with` block commits/closes,
    # so routes/stores can return ORM objects without a detached-instance error.
    session = AsyncSession(engine, expire_on_commit=False)
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
