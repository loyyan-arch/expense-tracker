def register_and_login(client, username):
    credentials = {
        "username": username,
        "password": "test-password-for-learning!",
    }

    response = client.post(
        "/auth/register",
        json=credentials,
    )
    assert response.status_code == 201

    response = client.post(
        "/auth/login",
        json=credentials,
    )
    assert response.status_code == 200

    token = response.json()["access_token"]

    return {"Authorization": f"Bearer {token}"}


def create_bill(client, headers, kind, amount):
    response = client.post(
        "/transactions",
        headers=headers,
        json={
            "kind": kind,
            "amount_cents": amount,
            "category": "其他",
            "occurred_on": "2025-02-15",
            "note": "自动化测试",
        },
    )

    assert response.status_code == 201
    return response.json()


def test_other_user_cannot_access_bill(client):
    headers_a = register_and_login(client, "user_a")
    headers_b = register_and_login(client, "user_b")

    bill = create_bill(client, headers_a, "expense", 2500)
    path = f"/transactions/{bill['id']}"

    response = client.get(path, headers=headers_b)
    assert response.status_code == 404

    response = client.patch(
        path,
        headers=headers_b,
        json={"amount_cents": 1},
    )
    assert response.status_code == 404

    response = client.delete(path, headers=headers_b)
    assert response.status_code == 404

    # 不能只看 B 的错误码，还要确认 A 的数据确实没变。
    response = client.get(path, headers=headers_a)
    assert response.status_code == 200
    assert response.json() == bill


def test_list_and_statistics_are_isolated(client):
    headers_a = register_and_login(client, "user_a")
    headers_b = register_and_login(client, "user_b")

    bill_a = create_bill(client, headers_a, "income", 10000)
    bill_b = create_bill(client, headers_b, "expense", 300)

    cases = [
        (headers_a, bill_a, 10000, 0, 10000),
        (headers_b, bill_b, 0, 300, -300),
    ]

    for headers, own_bill, income, expense, balance in cases:
        response = client.get(
            "/transactions",
            headers=headers,
        )
        assert response.status_code == 200
        assert [item["id"] for item in response.json()] == [
            own_bill["id"]
        ]

        response = client.get(
            "/statistics/monthly",
            headers=headers,
            params={"month": "2025-02"},
        )
        assert response.status_code == 200
        assert response.json() == {
            "month": "2025-02",
            "income_cents": income,
            "expense_cents": expense,
            "balance_cents": balance,
        }


def test_client_cannot_set_owner(client):
    headers = register_and_login(client, "user_a")

    response = client.post(
        "/transactions",
        headers=headers,
        json={
            "kind": "expense",
            "amount_cents": 100,
            "category": "其他",
            "occurred_on": "2025-02-15",
            "note": "伪造归属测试",
            "user_id": 999,
        },
    )

    assert response.status_code == 422

    response = client.get("/transactions", headers=headers)
    assert response.status_code == 200
    assert response.json() == []