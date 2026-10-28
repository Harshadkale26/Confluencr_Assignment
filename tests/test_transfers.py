def _account(client, name):
    return client.post("/accounts", json={"name": name}).json()


def _credit(client, account_id, amount, reference_id):
    return client.post(
        f"/accounts/{account_id}/transactions",
        json={"type": "credit", "amount": amount, "reference_id": reference_id},
    )


def test_transfer_moves_funds_atomically(client):
    source = _account(client, "A")
    destination = _account(client, "B")
    _credit(client, source["id"], "100.00", "seed-a")
    _credit(client, destination["id"], "50.00", "seed-b")

    response = client.post(
        "/transfers",
        json={
            "source_account_id": source["id"],
            "destination_account_id": destination["id"],
            "amount": "30.00",
            "reference_id": "xfer-1",
            "description": "rent",
        },
    )
    assert response.status_code == 201
    assert client.get(f"/accounts/{source['id']}/balance").json()["balance"] == "70.00"
    assert client.get(f"/accounts/{destination['id']}/balance").json()["balance"] == "80.00"

    source_history = client.get(f"/accounts/{source['id']}/transactions").json()
    dest_history = client.get(f"/accounts/{destination['id']}/transactions").json()
    assert any(item["type"] == "debit" and item["amount"] == "30.00" for item in source_history["transactions"])
    assert any(item["type"] == "credit" and item["amount"] == "30.00" for item in dest_history["transactions"])


def test_transfer_rejected_when_source_lacks_funds(client):
    source = _account(client, "A")
    destination = _account(client, "B")
    _credit(client, source["id"], "10.00", "seed-a")

    response = client.post(
        "/transfers",
        json={
            "source_account_id": source["id"],
            "destination_account_id": destination["id"],
            "amount": "30.00",
            "reference_id": "xfer-poor",
        },
    )
    assert response.status_code == 422
    assert client.get(f"/accounts/{source['id']}/balance").json()["balance"] == "10.00"
    assert client.get(f"/accounts/{destination['id']}/balance").json()["balance"] == "0.00"


def test_transfer_requires_both_accounts(client):
    source = _account(client, "A")
    _credit(client, source["id"], "10.00", "seed-a")
    response = client.post(
        "/transfers",
        json={
            "source_account_id": source["id"],
            "destination_account_id": "missing",
            "amount": "5.00",
            "reference_id": "xfer-missing",
        },
    )
    assert response.status_code == 404


def test_duplicate_transfer_reference(client):
    source = _account(client, "A")
    destination = _account(client, "B")
    _credit(client, source["id"], "100.00", "seed-a")
    payload = {
        "source_account_id": source["id"],
        "destination_account_id": destination["id"],
        "amount": "10.00",
        "reference_id": "xfer-dup",
    }
    first = client.post("/transfers", json=payload)
    second = client.post("/transfers", json=payload)
    assert first.status_code == 201
    assert second.status_code == 409
    assert client.get(f"/accounts/{source['id']}/balance").json()["balance"] == "90.00"


def test_cannot_transfer_to_same_account(client):
    account = _account(client, "A")
    _credit(client, account["id"], "20.00", "seed")
    response = client.post(
        "/transfers",
        json={
            "source_account_id": account["id"],
            "destination_account_id": account["id"],
            "amount": "5.00",
            "reference_id": "xfer-same",
        },
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "SAME_ACCOUNT_TRANSFER"
