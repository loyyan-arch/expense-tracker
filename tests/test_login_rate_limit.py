import rate_limit
from rate_limit import LoginRateLimiter
from routers import auth


def test_login_returns_429_and_recovers(client, monkeypatch):
    current_time = 100.0
    monkeypatch.setattr(
        rate_limit,
        "monotonic",
        lambda: current_time,
    )
    monkeypatch.setattr(
        auth,
        "login_limiter",
        LoginRateLimiter(limit=2, window_seconds=60),
    )

    credentials = {
        "username": "rate_limit_user",
        "password": "test-password-for-rate-limit!",
    }

    response = client.post("/auth/register", json=credentials)
    assert response.status_code == 201

    wrong_credentials = {
        **credentials,
        "password": "wrong-password",
    }

    for _ in range(2):
        response = client.post(
            "/auth/login",
            json=wrong_credentials,
        )
        assert response.status_code == 401

    # 额度已用完，即使密码正确，也要暂时拒绝。
    response = client.post("/auth/login", json=credentials)
    assert response.status_code == 429
    assert response.headers["retry-after"] == "60"
    assert "access_token" not in response.json()

    # 窗口到期后，正常登录恢复。
    current_time = 160.0

    response = client.post("/auth/login", json=credentials)
    assert response.status_code == 200
    assert response.json()["access_token"]