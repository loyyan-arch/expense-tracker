from sqlalchemy.exc import SQLAlchemyError

from db import get_db
from main import app


def test_health_is_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_returns_503_when_database_fails(client, monkeypatch):
    class BrokenSession:
        def execute(self, statement):
            raise SQLAlchemyError("模拟数据库不可用")

    def broken_get_db():
        yield BrokenSession()

    monkeypatch.setitem(
        app.dependency_overrides,
        get_db,
        broken_get_db,
    )

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"detail": "服务暂不可用"}