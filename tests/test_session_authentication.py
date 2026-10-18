import login_sessions


def register_account(client):
    credentials = {
        "username": "session_api_user",
        "password": "test-password-123",
    }

    response = client.post("/auth/register", json=credentials)
    assert response.status_code == 201

    return credentials


def login_headers(client, credentials):
    response = client.post("/auth/login", json=credentials)
    assert response.status_code == 200

    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_logout_invalidates_current_session_only(client):
    credentials = register_account(client)

    first = login_headers(client, credentials)
    second = login_headers(client, credentials)

    assert first != second
    assert client.get("/auth/me", headers=first).status_code == 200

    response = client.post("/auth/logout", headers=first)
    assert response.status_code == 204
    assert response.content == b""

    # 已退出的凭证无法再访问用户信息和账单。
    assert client.get("/auth/me", headers=first).status_code == 401
    assert client.get("/transactions", headers=first).status_code == 401

    # 同一账号的另一个会话不受影响。
    assert client.get("/auth/me", headers=second).status_code == 200

    # 重复使用已经撤销的凭证，返回未登录。
    assert client.post("/auth/logout", headers=first).status_code == 401


def test_expired_session_cannot_access_api(client, monkeypatch):
    credentials = register_account(client)

    monkeypatch.setattr(
        login_sessions, "now_timestamp", lambda: 1000
    )
    headers = login_headers(client, credentials)

    deadline = 1000 + login_sessions.SESSION_TTL_SECONDS

    monkeypatch.setattr(
        login_sessions, "now_timestamp", lambda: deadline - 1
    )
    assert client.get("/auth/me", headers=headers).status_code == 200

    monkeypatch.setattr(
        login_sessions, "now_timestamp", lambda: deadline
    )
    assert client.get("/auth/me", headers=headers).status_code == 401
    assert client.get("/transactions", headers=headers).status_code == 401


def test_logout_requires_authentication(client):
    response = client.post("/auth/logout")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"