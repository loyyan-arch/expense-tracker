import os
import secrets

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import URL, create_engine, event

# 必须放在导入 main 前面，仅影响本次测试进程。
os.environ["JWT_SECRET"] = secrets.token_hex(32)

import main
from db import Base, enable_foreign_keys


@pytest.fixture
def client(tmp_path, monkeypatch):
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

    # 当前所有接口都使用 main 模块里的 engine。
    monkeypatch.setattr(main, "engine", test_engine)

    try:
        Base.metadata.create_all(test_engine)

        with TestClient(main.app) as test_client:
            yield test_client
    finally:
        test_engine.dispose()