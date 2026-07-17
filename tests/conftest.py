import os
from pathlib import Path

# Everything in this block must precede any `from app...` import (pydantic-settings
# reads these at import time).

# In-memory rather than the docker-compose Postgres, so the suite runs fast and
# isolated without requiring that container up - each test gets its own fresh DB
# via the db_engine/db_session fixtures below anyway.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
# Explicit "memory://" rather than left unset, so a developer's real .env REDIS_URL
# (pointing at the docker-compose Redis) can't leak into the test run and force
# rate-limit state to persist across test processes - tests always get a fresh
# in-process store.
os.environ["REDIS_URL"] = "memory://"

# Pinned explicitly rather than left to whatever's in a developer's local .env, so the
# suite's rate-limit tests (which assume these exact thresholds to actually trip a 429)
# can't silently pass or fail differently depending on unrelated local tuning (e.g.
# loosened values someone set for their own Playwright/e2e runs against this same backend).
os.environ["LOGIN_RATE_LIMIT_PER_EMAIL"] = "5/5minutes"
os.environ["LOGIN_RATE_LIMIT_PER_IP"] = "20/5minutes"
os.environ["REGISTER_RATE_LIMIT_PER_IP"] = "5/hour"
os.environ["STATS_RATE_LIMIT_PER_IP"] = "30/minute"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from testcontainers.postgres import PostgresContainer

from app.database import Base, get_db
from app.main import app
from app.rag.models import RAG_TABLE_NAMES
from app.rate_limit import reset_rate_limits

TEST_DATABASE_URL = "sqlite:///:memory:"

# Colima (a Docker Desktop alternative some contributors may run locally) exposes
# its Docker socket at a nonstandard, per-profile path instead of the conventional
# /var/run/docker.sock. testcontainers' cleanup sidecar (Ryuk, which guarantees our
# pg_engine container gets killed even if the test process is hard-killed rather
# than exiting cleanly) bind-mounts the host socket into its own container and
# expects to find it at that conventional path once mounted - on Colima that mount
# fails outright, so Ryuk fails to start and the RAG Postgres fixture never comes
# up. These two env vars are the documented fix: DOCKER_HOST points the Python
# Docker client at Colima's real socket, TESTCONTAINERS_DOCKER_SOCKET_OVERRIDE tells
# Ryuk what path to expect once mounted. Only applied when Colima's default-profile
# socket actually exists on disk, so this is a no-op on Docker Desktop, CI, or any
# non-default Colima profile - and setdefault() never overrides a DOCKER_HOST a
# developer has already set themselves. Safe to run after imports (unlike the env
# vars above) since testcontainers only reads these lazily, when a container is
# actually started by a test that requests pg_engine/pg_session - not at import time.
_colima_socket = Path.home() / ".colima" / "default" / "docker.sock"
if _colima_socket.exists():
    os.environ.setdefault("DOCKER_HOST", f"unix://{_colima_socket}")
    os.environ.setdefault("TESTCONTAINERS_DOCKER_SOCKET_OVERRIDE", "/var/run/docker.sock")

# SQLite has no equivalent of pgvector's `vector` column type, so tables built on
# KnowledgeChunkMixin (see app/rag/models.py) are excluded here and exercised
# against a real Postgres+pgvector container instead (pg_engine/pg_session below).
_SQLITE_TABLES = [table for table in Base.metadata.tables.values() if table.name not in RAG_TABLE_NAMES]
_RAG_TABLES = [table for table in Base.metadata.tables.values() if table.name in RAG_TABLE_NAMES]


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    # Rate-limit storage is an in-memory singleton shared across the whole test
    # process, not per-test like the DB fixtures below. Without this, rate limits
    # (e.g. register's 5/hour) would exhaust across the entire suite instead of
    # resetting per test, since nearly every test registers a user via the
    # registered_user_token/auth_headers fixtures.
    reset_rate_limits()
    yield
    reset_rate_limits()


@pytest.fixture
def db_engine():
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine, tables=_SQLITE_TABLES)
    yield engine
    Base.metadata.drop_all(bind=engine, tables=_SQLITE_TABLES)
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    session_local = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = session_local()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="session")
def pg_engine():
    # Session-scoped: one throwaway pgvector-enabled container for the whole test
    # run, not per test - container startup cost is real, and pg_session below
    # gives each test its own rolled-back transaction on top of this shared engine,
    # so tests still can't see each other's data.
    with PostgresContainer("pgvector/pgvector:pg17") as container:
        engine = create_engine(container.get_connection_url())
        with engine.begin() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        Base.metadata.create_all(bind=engine, tables=_RAG_TABLES)
        yield engine
        engine.dispose()


@pytest.fixture
def pg_session(pg_engine):
    connection = pg_engine.connect()
    transaction = connection.begin()
    session_local = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    session = session_local()
    try:
        yield session
    finally:
        session.close()
        # A failed commit (e.g. a CheckConstraint violation) already deassociates
        # the transaction internally - rolling back again would just be a no-op
        # SAWarning, not a real double-rollback bug.
        if transaction.is_active:
            transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def registered_user_token(client):
    payload = {"name": "Test User", "email": "test@example.com", "password": "supersecret123"}
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 201
    return {"token": response.json()["access_token"], "email": payload["email"], "password": payload["password"]}


@pytest.fixture
def auth_headers(registered_user_token):
    return {"Authorization": f"Bearer {registered_user_token['token']}"}
