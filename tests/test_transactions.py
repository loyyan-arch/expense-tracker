import pytest


@pytest.fixture
def auth_headers(client):
    credentials = {
        "username": "transaction_tester",
        "password": "test-password-for-transactions!",
    }

    response = client.post("/auth/register", json=credentials)
    assert response.status_code == 201

    response = client.post("/auth/login", json=credentials)
    assert response.status_code == 200

    return {
        "Authorization": f"Bearer {response.json()['access_token']}"
    }


@pytest.fixture
def valid_bill():
    return {
        "kind": "expense",
        "amount_cents": 2500,
        "category": "餐饮",
        "occurred_on": "2026-02-15",
        "note": "午饭",
    }

def test_transaction_lifecycle(client, auth_headers, valid_bill):
    response = client.post(
        "/transactions",
        headers=auth_headers,
        json=valid_bill,
    )
    assert response.status_code == 201

    created = response.json()
    path = f"/transactions/{created['id']}"

    # 创建后的数据必须能通过另一个请求查到。
    response = client.get(path, headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == created

    # 只修改金额。
    response = client.patch(
        path,
        headers=auth_headers,
        json={"amount_cents": 3000},
    )
    assert response.status_code == 200

    expected = {**created, "amount_cents": 3000}
    assert response.json() == expected

    # 再次查询，确认修改已持久化，其他字段保持原值。
    response = client.get(path, headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == expected

    response = client.delete(path, headers=auth_headers)
    assert response.status_code == 204
    assert response.content == b""

    # 删除不仅要返回成功，还必须真正查不到。
    response = client.get(path, headers=auth_headers)
    assert response.status_code == 404

    response = client.get("/transactions", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []

@pytest.mark.parametrize(
    "field,value",
    [
        pytest.param("amount_cents", 0, id="zero-amount"),
        pytest.param("amount_cents", -1, id="negative-amount"),
        pytest.param("amount_cents", 1.5, id="decimal-amount"),
        pytest.param("amount_cents", "100", id="string-amount"),
        pytest.param("amount_cents", True, id="boolean-amount"),
        pytest.param("occurred_on", "2026-02-30", id="invalid-date"),
        pytest.param("category", "旅游", id="unknown-category"),
    ],
)
def test_invalid_bill_is_not_saved(
    client, auth_headers, valid_bill, field, value
):
    payload = {**valid_bill, field: value}

    response = client.post(
        "/transactions",
        headers=auth_headers,
        json=payload,
    )

    assert response.status_code == 422

    # 确认报错确实来自本次故意修改的字段。
    errors = response.json()["detail"]
    assert any(
        error["loc"] == ["body", field]
        for error in errors
    )

    # 请求失败后不能留下账单。
    response = client.get("/transactions", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []