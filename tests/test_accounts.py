def test_create_account_starts_at_zero(client):
    response = client.post("/accounts", json={"name": "Ada Lovelace"})
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Ada Lovelace"
    assert body["balance"] == "0.00"
    assert body["id"]
    assert body["created_at"]


def test_create_account_ignores_client_balance(client):
    response = client.post("/accounts", json={"name": "Alan Turing", "balance": 999})
    assert response.status_code == 201
    assert response.json()["balance"] == "0.00"


def test_create_account_requires_name(client):
    response = client.post("/accounts", json={"name": "   "})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_get_balance(client):
    created = client.post("/accounts", json={"name": "Grace Hopper"}).json()
    response = client.get(f"/accounts/{created['id']}/balance")
    assert response.status_code == 200
    assert response.json() == {"account_id": created["id"], "balance": "0.00"}


def test_get_balance_not_found(client):
    response = client.get("/accounts/missing/balance")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ACCOUNT_NOT_FOUND"
