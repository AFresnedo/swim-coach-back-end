from collections.abc import Generator
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends
from sqlalchemy import DateTime, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.types import TypeDecorator

from app.db_config import database_settings

connect_args = {"check_same_thread": False} if database_settings.database_url.startswith("sqlite") else {}
engine = create_engine(database_settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class StandardBase(DeclarativeBase):
    """Declarative base for tables built from standard SQL types only.

    Runnable against any backend, including the SQLite test fixture. Tables
    that need a backend-specific type (e.g. pgvector's Vector column) belong
    on VectorBase instead - the split is by column shape, not by feature/domain,
    so a plain relational table that happens to support a RAG feature still
    belongs here.
    """

    pass


class VectorBase(DeclarativeBase):
    """Declarative base for tables that require the pgvector extension.

    Kept separate from StandardBase so pgvector-dependent tables (Vector
    columns, HNSW indexes) are structurally excluded from any sweep of
    StandardBase.metadata - e.g. the SQLite test fixture - without needing a
    manually maintained table-name allowlist.
    """

    pass


class UTCDateTime(TypeDecorator[datetime]):
    """DateTime(timezone=True), but always reads back tz-aware.

    Postgres round-trips a tz-aware value as tz-aware, but SQLite (tests, local
    dev) has no native tz-aware storage and always hands back naive - normalize
    here once, so no comparison site has to special-case SQLite itself.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_result_value(self, value: datetime | None, dialect: object) -> datetime | None:
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value


def check_connection() -> None:
    """Startup check: opens and immediately closes a real connection, so a bad
    DATABASE_URL (wrong host, bad credentials, unreachable server) fails loudly at
    process boot instead of surfacing on whichever request first needs the DB."""
    with engine.connect():
        pass


def get_db() -> Generator[Session]:
    db = SessionLocal()
    try:
        yield db
    except Exception:
        # Centralized safety net: any endpoint that lets a DB exception propagate
        # without its own try/except still gets an explicit rollback here, rather
        # than relying on Session.close() below to roll back implicitly. Endpoints
        # that need to keep using the session afterward (e.g. to recover from a
        # constraint race and retry) still need their own local rollback - this
        # only covers the case where the exception escapes the endpoint entirely.
        db.rollback()
        raise
    finally:
        db.close()


DbDep = Annotated[Session, Depends(get_db)]
