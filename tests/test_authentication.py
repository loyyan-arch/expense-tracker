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

    
@pytest.mark.parametrize(
    "username,expected_detail",
    [
        pytest.param(
            "existing_user",
            "密码错误",
            id="wrong-password",
        ),
        pytest.param(
            "missing_user",
            "用户名不存在，请先注册",
            id="unknown-user",
        ),
    ],
)
def test_login_failure_messages(client, username, expected_detail):
    response = client.post(
        "/auth/register",
        json={
            "username": "existing_user",
            "password": "correct-password-for-testing!",
        },
    )
    assert response.status_code == 201

    response = client.post(
        "/auth/login",
        json={
            "username": username,
            "password": "wrong-password-for-testing!",
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": expected_detail,
    }
    assert "access_token" not in response.json()

def test_duplicate_registration_preserves_original_account(client):
    original = {
        "username": "duplicate_user",
        "password": "original-password-for-testing!",
    }

    response = client.post("/auth/register", json=original)
    assert response.status_code == 201
    original_user_id = response.json()["id"]

    replacement = {
        **original,
        "password": "replacement-password-for-testing!",
    }

    # 同名注册必须被拒绝。
    response = client.post("/auth/register", json=replacement)
    assert response.status_code == 409
    assert response.json() == {
        "detail": "用户名已存在",
    }

    # 原账号、原密码仍然有效。
    response = client.post("/auth/login", json=original)
    assert response.status_code == 200

    token = response.json()["access_token"]
    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json() == {
        "id": original_user_id,
        "username": original["username"],
    }

    # 被拒绝的注册请求不能修改原密码。
    response = client.post("/auth/login", json=replacement)
    assert response.status_code == 401
    assert response.json() == {
        "detail": "密码错误",
    }
    assert "access_token" not in response.json()


@pytest.mark.parametrize(
    "path,password",
    [
        pytest.param(
            "/auth/register",
            "Ab9!xy",
            id="registration-password-too-short",
        ),
        pytest.param(
            "/auth/register",
            "A" * 129,
            id="registration-password-too-long",
        ),
        pytest.param(
            "/auth/login",
            "B" * 129,
            id="login-password-too-long",
        ),
    ],
)
def test_password_validation_does_not_echo_input(client, path, password):
    response = client.post(
        path,
        json={
            "username": "validation_user",
            "password": password,
        },
    )

    assert response.status_code == 422

    errors = response.json()["detail"]

    # 确认确实是密码字段校验失败。
    assert any(
        error["loc"] == ["body", "password"]
        for error in errors
    )

    # 错误响应不应回显原始输入。
    assert password not in response.text
    assert all("input" not in error for error in errors)


@pytest.mark.parametrize(
    "length,expected_status",
    [
        pytest.param(6, 422, id="below-minimum"),
        pytest.param(7, 201, id="at-minimum"),
        pytest.param(128, 201, id="at-maximum"),
        pytest.param(129, 422, id="above-maximum"),
    ],
)
def test_registration_password_length(
    client, length, expected_status
):
    credentials = {
        "username": "password_boundary_user",
        "password": "Ab9!" + "x" * (length - 4),
    }

    response = client.post("/auth/register", json=credentials)
    assert response.status_code == expected_status

    if expected_status == 201:
        # 边界长度不仅要能注册，还必须能正常登录。
        user_id = response.json()["id"]

        response = client.post("/auth/login", json=credentials)
        assert response.status_code == 200

        token = response.json()["access_token"]
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["id"] == user_id
    else:
        assert any(
            error["loc"] == ["body", "password"]
            for error in response.json()["detail"]
        )

