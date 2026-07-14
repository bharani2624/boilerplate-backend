"""Single shared engine for the Supabase Postgres database.

Why this file exists: every store (src/store/*.py) needs a database session, and they
all need to share one connection pool rather than each opening its own. This module is
the one place that creates the SQLAlchemy `engine` and hands out sessions from it.
"""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from config.settings import settings

# pool_pre_ping=True: check a pooled connection is still alive before using it — Supabase's
# pooler (and most managed Postgres) will silently drop idle connections, and without this
# the first query after a lull would fail with "server closed the connection unexpectedly."
engine: Engine = create_engine(
    settings.database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_pre_ping=True,
)


def create_db_and_tables() -> None:
    """Create tables that don't exist yet. Safe to call on every startup.

    Every SQLModel class with table=True that has been imported (see
    database/models/__init__.py) registers itself on SQLModel.metadata; create_all
    only issues CREATE TABLE for the ones that aren't already in the database, so this
    never touches tables that already exist.
    """
    SQLModel.metadata.create_all(engine)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Yield a session, commit on success, rollback on error, always close.

    Stores use this as `with self.get_session() as session:` so none of them need to
    remember to commit/rollback/close themselves — one bug here is fixed everywhere.
    """
    # expire_on_commit=False: objects stay usable after the `with` block commits/closes,
    # so routes/stores can return ORM objects without a detached-instance error.
    session = Session(engine, expire_on_commit=False)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
