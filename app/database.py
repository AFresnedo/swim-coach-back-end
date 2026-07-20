from collections.abc import Generator
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends
from sqlalchemy import DateTime, create_engine
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
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


def _conflict_insert[ModelT: DeclarativeBase](db: Session, model: type[ModelT]):
    """Return the dialect-specific INSERT construct that supports ON CONFLICT.

    SQLAlchemy has no backend-neutral ON CONFLICT: the Postgres and SQLite
    dialects each ship their own insert() with the on_conflict_* methods, and the
    generic construct has neither. Both backends run in this project (Postgres in
    prod, SQLite in tests/local dev), so the one spot where the two dialects
    diverge is isolated here rather than leaking into every call site.
    """
    dialect = db.get_bind().dialect.name
    if dialect == "postgresql":
        return pg_insert(model)
    if dialect == "sqlite":
        return sqlite_insert(model)
    raise RuntimeError(f"ON CONFLICT upsert is not implemented for the {dialect!r} dialect")


def upsert_returning[ModelT: DeclarativeBase](
    db: Session,
    model: type[ModelT],
    *,
    values: dict[str, object],
    conflict_columns: list[str],
    update_columns: list[str],
) -> ModelT:
    """INSERT `values`, or UPDATE `update_columns` if a row already exists on the
    `conflict_columns` unique index - one atomic statement, so there's no
    read-then-write window for two concurrent first-time writers to race through.
    Returns the resulting row as a live ORM instance, taken from the statement's
    RETURNING clause so it reflects exactly what was persisted.

    `conflict_columns` must name a real unique constraint/index: ON CONFLICT only
    absorbs a collision on that specific target, so a violation of any other
    constraint still raises rather than being silently swallowed.
    """
    statement = _conflict_insert(db, model).values(**values)
    statement = statement.on_conflict_do_update(
        index_elements=conflict_columns,
        set_={column: statement.excluded[column] for column in update_columns},
    ).returning(model)
    # populate_existing overwrites any stale copy of this row already in the
    # session's identity map with the RETURNING values, so the returned instance
    # can't shadow the write with a pre-write cached state.
    return db.execute(statement, execution_options={"populate_existing": True}).scalars().one()


def insert_skip_on_conflict[ModelT: DeclarativeBase](
    db: Session,
    model: type[ModelT],
    *,
    values: dict[str, object],
    conflict_columns: list[str],
) -> ModelT | None:
    """INSERT `values`, or skip the write if a row already exists on the
    `conflict_columns` unique index - one atomic statement, no read-then-INSERT
    race window. Returns the newly inserted row as a live ORM instance, or None if
    the row already existed (nothing was inserted) - the caller still learns which
    case happened via that return value, the conflict itself isn't swallowed, only
    the write and the INSERT-time error are skipped.

    `conflict_columns` must name a real unique constraint/index: a collision on any
    other constraint still raises rather than being absorbed here.
    """
    statement = (
        _conflict_insert(db, model)
        .values(**values)
        .on_conflict_do_nothing(index_elements=conflict_columns)
        .returning(model)
    )
    return db.execute(statement, execution_options={"populate_existing": True}).scalars().one_or_none()


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
