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


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({}, id="empty-update"),
        pytest.param(
            {"amount_cents": None},
            id="null-amount",
        ),
        pytest.param(
            {"amount_cents": 0},
            id="zero-amount",
        ),
        pytest.param(
            {"amount_cents": -1},
            id="negative-amount",
        ),
        pytest.param(
            {"amount_cents": 1.5},
            id="decimal-amount",
        ),
        pytest.param(
            {"amount_cents": "100"},
            id="string-amount",
        ),
        pytest.param(
            {"amount_cents": True},
            id="boolean-amount",
        ),
        pytest.param(
            {"note": "不应该保存的备注", "amount_cents": -1},
            id="mixed-valid-and-invalid-fields",
        ),
        pytest.param(
            {"user_id": 999},
            id="cannot-change-owner",
        ),
    ],
)
def test_invalid_update_preserves_bill(
    client, auth_headers, valid_bill, payload
):
    # 准备一笔真实存在的账单。
    response = client.post(
        "/transactions",
        headers=auth_headers,
        json=valid_bill,
    )
    assert response.status_code == 201

    original = response.json()
    path = f"/transactions/{original['id']}"

    # 尝试非法修改。
    response = client.patch(
        path,
        headers=auth_headers,
        json=payload,
    )
    assert response.status_code == 422

    # 用新的查询请求，验证保存的数据没有变化。
    response = client.get(path, headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == original


@pytest.fixture
def create_bill(client, auth_headers, valid_bill):
    def create(**changes):
        response = client.post(
            "/transactions",
            headers=auth_headers,
            json={**valid_bill, **changes},
        )
        assert response.status_code == 201
        return response.json()

    return create


def test_pagination_returns_expected_records(
    client, auth_headers, create_bill
):
    bills = [create_bill(amount_cents=100) for _ in range(5)]
    expected_ids = [bill["id"] for bill in reversed(bills)]

    cases = [
        (0, expected_ids[0:2]),
        (2, expected_ids[2:4]),
        (4, expected_ids[4:5]),
        (5, []),
    ]

    for offset, expected_page in cases:
        response = client.get(
            "/transactions",
            headers=auth_headers,
            params={"offset": offset, "limit": 2},
        )
        assert response.status_code == 200
        assert [
            bill["id"] for bill in response.json()
        ] == expected_page


@pytest.mark.parametrize(
    "params",
    [
        pytest.param({"offset": -1}, id="negative-offset"),
        pytest.param({"limit": 0}, id="zero-limit"),
        pytest.param({"limit": 101}, id="limit-too-large"),
    ],
)
def test_invalid_pagination_is_rejected(client, auth_headers, params):
    response = client.get(
        "/transactions",
        headers=auth_headers,
        params=params,
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "month,before,first,last,after",
    [
        pytest.param(
            "2026-02",
            "2026-01-31",
            "2026-02-01",
            "2026-02-28",
            "2026-03-01",
            id="ordinary-month",
        ),
        pytest.param(
            "2026-12",
            "2026-11-30",
            "2026-12-01",
            "2026-12-31",
            "2027-01-01",
            id="year-boundary",
        ),
        pytest.param(
            "2028-02",
            "2028-01-31",
            "2028-02-01",
            "2028-02-29",
            "2028-03-01",
            id="leap-year",
        ),
    ],
)
def test_monthly_list_and_statistics_respect_boundaries(
    client, auth_headers, create_bill,
    month, before, first, last, after
):
    create_bill(
        kind="expense", amount_cents=900, occurred_on=before
    )
    first_bill = create_bill(
        kind="income", amount_cents=1000, occurred_on=first
    )
    last_bill = create_bill(
        kind="expense", amount_cents=300, occurred_on=last
    )
    create_bill(
        kind="income", amount_cents=8000, occurred_on=after
    )

    response = client.get(
        "/transactions",
        headers=auth_headers,
        params={"month": month},
    )
    assert response.status_code == 200
    assert [
        bill["id"] for bill in response.json()
    ] == [last_bill["id"], first_bill["id"]]

    response = client.get(
        "/statistics/monthly",
        headers=auth_headers,
        params={"month": month},
    )
    assert response.status_code == 200
    assert response.json() == {
        "month": month,
        "income_cents": 1000,
        "expense_cents": 300,
        "balance_cents": 700,
    }


def test_empty_month_has_no_records_and_zero_totals(
    client, auth_headers, create_bill
):
    create_bill(
        kind="income",
        amount_cents=5000,
        occurred_on="2026-01-15",
    )

    response = client.get(
        "/transactions",
        headers=auth_headers,
        params={"month": "2026-02"},
    )
    assert response.status_code == 200
    assert response.json() == []

    response = client.get(
        "/statistics/monthly",
        headers=auth_headers,
        params={"month": "2026-02"},
    )
    assert response.status_code == 200
    assert response.json() == {
        "month": "2026-02",
        "income_cents": 0,
        "expense_cents": 0,
        "balance_cents": 0,
    }