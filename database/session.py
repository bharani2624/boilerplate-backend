"""Single shared engine for the Supabase Postgres database."""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from config.settings import settings

engine: Engine = create_engine(
    settings.database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_pre_ping=True,
)


def create_db_and_tables() -> None:
    """Create tables that don't exist yet. Safe to call on every startup."""
    SQLModel.metadata.create_all(engine)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Yield a session, commit on success, rollback on error, always close."""
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
