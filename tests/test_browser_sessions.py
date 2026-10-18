import pytest
import login_sessions
from browser_session import COOKIE_NAME
from config import settings

CSRF = {"X-CSRF-Protection": "1", "Origin": "http://localhost:5173"}
ACCOUNT = {"username": "browser_user", "password": "browser-password-123"}
BILL = {"kind": "expense", "amount_cents": 123, "category": "其他",
        "occurred_on": "2026-10-18", "note": "cookie test"}


@pytest.fixture
def browser(client, monkeypatch):
    monkeypatch.setattr(settings, "session_cookie_secure", False)
    monkeypatch.setattr(settings, "browser_origins", ["http://localhost:5173"])
    assert client.post("/auth/register", json=ACCOUNT).status_code == 201
    return client


def sign_in(browser):
    response = browser.post("/auth/browser/login", json=ACCOUNT, headers=CSRF)
    assert response.status_code == 200
    return response


def test_cookie_login_restore_write_and_logout(browser):
    response = sign_in(browser)
    assert set(response.json()) == {"id", "username"}
    cookie = response.headers["set-cookie"]
    for attribute in ("HttpOnly", "Max-Age=604800", "Path=/", "SameSite=lax"):
        assert attribute in cookie
    token = browser.cookies.get(COOKIE_NAME)
    assert token not in response.text
    me = browser.get("/auth/me")
    assert me.status_code == 200
    assert me.headers["cache-control"] == "no-store"
    created = browser.post("/transactions", json=BILL, headers=CSRF)
    assert created.status_code == 201
    bill_id = created.json()["id"]
    assert browser.patch(f"/transactions/{bill_id}", json={"note": "edited"}, headers=CSRF).status_code == 200
    assert browser.delete(f"/transactions/{bill_id}", headers=CSRF).status_code == 204
    response = browser.post("/auth/browser/logout", headers=CSRF)
    assert response.status_code == 204
    assert "Max-Age=0" in response.headers["set-cookie"]
    assert browser.cookies.get(COOKIE_NAME) is None
    assert browser.get("/auth/me").status_code == 401
    assert browser.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401
    assert browser.post("/auth/browser/logout", headers=CSRF).status_code == 204


@pytest.mark.parametrize("headers", [
    {}, {"Origin": "http://localhost:5173"},
    {"X-CSRF-Protection": "1", "Origin": "https://evil.example"},
    {"X-CSRF-Protection": "1", "Origin": "null"},
    {**CSRF, "Sec-Fetch-Site": "cross-site"},
])
def test_csrf_rejects_login_writes_and_logout(browser, headers):
    assert browser.post("/auth/browser/login", json=ACCOUNT, headers=headers).status_code == 403
    sign_in(browser)
    assert browser.post("/transactions", json=BILL, headers=headers).status_code == 403
    assert browser.patch("/transactions/1", json={"note": "bad"}, headers=headers).status_code == 403
    assert browser.delete("/transactions/1", headers=headers).status_code == 403
    assert browser.post("/auth/browser/logout", headers=headers).status_code == 403
    assert browser.get("/auth/me").status_code == 200
    assert browser.get("/transactions").json() == []


def test_no_origin_requires_custom_header_and_no_cors(browser):
    assert browser.post("/auth/browser/login", json=ACCOUNT,
                        headers={"X-CSRF-Protection": "1"}).status_code == 200
    response = browser.options("/transactions", headers={
        "Origin": "https://evil.example", "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "X-CSRF-Protection",
    })
    assert "access-control-allow-origin" not in response.headers


@pytest.mark.parametrize("authorization", ["Bearer bad", "Basic bad", "Bearer"])
def test_bad_authorization_never_falls_back_to_valid_cookie(browser, authorization):
    sign_in(browser)
    assert browser.get("/auth/me", headers={"Authorization": authorization}).status_code == 401


def test_fixed_expiration_and_expired_logout(browser, monkeypatch):
    monkeypatch.setattr(login_sessions, "now_timestamp", lambda: 1000)
    sign_in(browser)
    deadline = 1000 + login_sessions.SESSION_TTL_SECONDS
    monkeypatch.setattr(login_sessions, "now_timestamp", lambda: deadline - 1)
    response = browser.get("/auth/me")
    assert response.status_code == 200
    assert "set-cookie" not in response.headers
    monkeypatch.setattr(login_sessions, "now_timestamp", lambda: deadline)
    assert browser.get("/auth/me").status_code == 401
    assert browser.post("/auth/browser/logout", headers=CSRF).status_code == 204
    assert browser.cookies.get(COOKIE_NAME) is None


def test_rotation_and_other_device_survives(browser):
    other = browser.post("/auth/login", json=ACCOUNT).json()["access_token"]
    sign_in(browser)
    old = browser.cookies.get(COOKIE_NAME)
    sign_in(browser)
    assert browser.cookies.get(COOKIE_NAME) != old
    assert browser.get("/auth/me", headers={"Authorization": f"Bearer {old}"}).status_code == 401
    assert browser.post("/auth/browser/logout", headers=CSRF).status_code == 204
    assert browser.get("/auth/me", headers={"Authorization": f"Bearer {other}"}).status_code == 200


def test_secure_cookie_on_https_configuration(browser, monkeypatch):
    monkeypatch.setattr(settings, "session_cookie_secure", True)
    assert "Secure" in sign_in(browser).headers["set-cookie"]


def test_browser_and_bearer_share_login_rate_limit(browser):
    for _ in range(5):
        assert browser.post("/auth/login", json=ACCOUNT).status_code == 200
    assert browser.post("/auth/browser/login", json=ACCOUNT, headers=CSRF).status_code == 429
