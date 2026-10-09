import pytest
from datetime import datetime, timedelta, timezone
import secrets

import jwt
import security

@pytest.mark.parametrize(
    "method,path,body",
    [
        ("GET", "/auth/me", None),
        ("GET", "/transactions", None),
        ("GET", "/transactions/1", None),
        ("DELETE", "/transactions/1", None),
        (
            "PATCH",
            "/transactions/1",
            {"amount_cents": 100},
        ),
        (
            "POST",
            "/transactions",
            {
                "kind": "expense",
                "amount_cents": 100,
                "category": "其他",
                "occurred_on": "2025-02-15",
                "note": "未登录测试",
            },
        ),
        (
            "GET",
            "/statistics/monthly?month=2025-02",
            None,
        ),
    ],
)
def test_login_is_required(client, method, path, body):
    options = {}

    if body is not None:
        options["json"] = body

    response = client.request(method, path, **options)

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize(
    "authorization",
    [
        "Bearer not-a-valid-token",
        "Basic invalid-credentials",
    ],
)
def test_invalid_credentials_are_rejected(client, authorization):
    response = client.get(
        "/auth/me",
        headers={"Authorization": authorization},
    )

    assert response.status_code == 401

@pytest.mark.parametrize("case", ["wrong_signature", "expired"])
def test_invalid_signed_token_is_rejected(client, case):
    credentials = {
        "username": "token_test_user",
        "password": "test-password-for-learning!",
    }

    response = client.post("/auth/register", json=credentials)
    assert response.status_code == 201
    user_id = response.json()["id"]

    # 先确认这个用户正常登录得到的 token 能通过验证。
    response = client.post("/auth/login", json=credentials)
    assert response.status_code == 200

    valid_token = response.json()["access_token"]

    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {valid_token}"},
    )
    assert response.status_code == 200
    assert response.json()["id"] == user_id

    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now - timedelta(minutes=2),
        "exp": now + timedelta(minutes=30),
    }
    signing_key = security.JWT_SECRET

    if case == "wrong_signature":
        # 内容和有效期都合法，但用另一个密钥签名。
        signing_key = secrets.token_hex(32)
    else:
        # 使用正确密钥，但有效期已经结束。
        payload["exp"] = now - timedelta(minutes=1)

    invalid_token = jwt.encode(
        payload,
        signing_key,
        algorithm=security.JWT_ALGORITHM,
    )

    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {invalid_token}"},
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"