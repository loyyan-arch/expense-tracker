import pytest


def login_as(client, username):
    credentials = {"username": username, "password": "yearly-test-password"}
    assert client.post("/auth/register", json=credentials).status_code == 201
    response = client.post("/auth/login", json=credentials)
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def add_bill(client, headers, day, kind, amount):
    response = client.post("/transactions", headers=headers, json={
        "kind": kind, "amount_cents": amount, "category": "其他",
        "occurred_on": day, "note": "annual test",
    })
    assert response.status_code == 201
    return response.json()["id"]


def test_yearly_boundaries_leap_day_and_user_isolation(client):
    headers = login_as(client, "year_owner")
    other = login_as(client, "year_other")
    add_bill(client, headers, "2023-12-31", "income", 99999)
    add_bill(client, headers, "2024-01-01", "income", 10000)
    add_bill(client, headers, "2024-02-29", "expense", 2550)
    add_bill(client, headers, "2024-12-31", "expense", 8000)
    add_bill(client, headers, "2025-01-01", "expense", 99999)
    add_bill(client, other, "2024-02-29", "income", 99999)
    response = client.get("/statistics/yearly?year=2024", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert (data["income_cents"], data["expense_cents"], data["balance_cents"]) == (10000, 10550, -550)
    assert [item["month"] for item in data["months"]] == [f"2024-{m:02d}" for m in range(1, 13)]
    assert data["months"][1]["expense_cents"] == 2550
    assert data["months"][2]["balance_cents"] == 0
    for field in ("income_cents", "expense_cents", "balance_cents"):
        assert sum(month[field] for month in data["months"]) == data[field]


@pytest.mark.parametrize("year", [1, 2026, 9998])
def test_empty_year_has_twelve_zero_months(client, year):
    headers = login_as(client, "empty_year")
    response = client.get(f"/statistics/yearly?year={year}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["year"] == year
    assert data["months"] == [
        {"month": f"{year:04d}-{m:02d}", "income_cents": 0,
         "expense_cents": 0, "balance_cents": 0} for m in range(1, 13)
    ]


@pytest.mark.parametrize("year", ["0", "9999", "-1", "abc", "2024.5"])
def test_invalid_year(client, year):
    headers = login_as(client, "invalid_year")
    assert client.get(f"/statistics/yearly?year={year}", headers=headers).status_code == 422


def test_year_requires_authentication(client):
    assert client.get("/statistics/yearly?year=2026").status_code == 401


def test_edit_across_years_and_delete_recalculate(client):
    headers = login_as(client, "move_year")
    bill_id = add_bill(client, headers, "2025-12-31", "expense", 29)
    assert client.patch(f"/transactions/{bill_id}", headers=headers,
                        json={"occurred_on": "2026-01-01"}).status_code == 200
    old = client.get("/statistics/yearly?year=2025", headers=headers).json()
    new = client.get("/statistics/yearly?year=2026", headers=headers).json()
    assert old["expense_cents"] == 0
    assert new["expense_cents"] == 29
    assert new["balance_cents"] == -29
    assert client.delete(f"/transactions/{bill_id}", headers=headers).status_code == 204
    assert client.get("/statistics/yearly?year=2026", headers=headers).json()["expense_cents"] == 0


def test_annual_includes_more_than_one_page_and_agrees_with_monthly(client):
    headers = login_as(client, "all_pages")
    for _ in range(12):
        add_bill(client, headers, "2026-03-15", "income", 101)
    annual = client.get("/statistics/yearly?year=2026", headers=headers).json()
    monthly = client.get("/statistics/monthly?month=2026-03", headers=headers).json()
    assert annual["income_cents"] == 1212
    assert annual["months"][2] == monthly
