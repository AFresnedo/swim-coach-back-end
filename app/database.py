from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


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
