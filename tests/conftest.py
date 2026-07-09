import os

# Everything in this block must precede any `from app...` import (pydantic-settings
# reads these at import time).

# In-memory rather than the docker-compose Postgres, so the suite runs fast and
# isolated without requiring that container up - each test gets its own fresh DB
# via the db_engine/db_session fixtures below anyway.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
# Blank rather than left unset, so a developer's real .env REDIS_URL (pointing at the
# docker-compose Redis) can't leak into the test run and force rate-limit state to
# persist across test processes - tests always get a fresh in-process MemoryStorage.
os.environ["REDIS_URL"] = ""

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
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.rate_limit import reset_rate_limits

TEST_DATABASE_URL = "sqlite:///:memory:"


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
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    session_local = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = session_local()
    try:
        yield session
    finally:
        session.close()


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
