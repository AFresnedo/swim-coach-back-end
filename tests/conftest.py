import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"  # must precede any `from app...` import

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = "sqlite:///:memory:"


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
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestingSessionLocal()
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
