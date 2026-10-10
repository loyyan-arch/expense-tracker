import os
import secrets

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import URL, create_engine, event
from sqlalchemy.orm import Session


os.environ["JWT_SECRET"] = secrets.token_hex(32)

import main
from db import Base, enable_foreign_keys, get_db
from rate_limit import LoginRateLimiter
from routers import auth


@pytest.fixture
def client(tmp_path):
    test_engine = create_engine(
        URL.create(
            "sqlite",
            database=str(tmp_path / "test.db"),
        ),
    )

    event.listen(
        test_engine,
        "connect",
        enable_foreign_keys,
    )

    def override_get_db():
        with Session(test_engine) as session:
            yield session

    try:
        Base.metadata.create_all(test_engine)

        main.app.dependency_overrides[get_db] = override_get_db

        with TestClient(main.app) as test_client:
            yield test_client
    finally:
        main.app.dependency_overrides.pop(get_db, None)
        test_engine.dispose()

@pytest.fixture(autouse=True)
def fresh_login_limiter(monkeypatch):
    monkeypatch.setattr(
        auth,
        "login_limiter",
        LoginRateLimiter(limit=5, window_seconds=60),
    )