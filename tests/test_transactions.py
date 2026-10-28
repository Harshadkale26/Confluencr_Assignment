def _account(client, name="Holder"):
    return client.post("/accounts", json={"name": name}).json()


def _txn(client, account_id, txn_type, amount, reference_id, description=None):
    payload = {
        "type": txn_type,
        "amount": amount,
        "reference_id": reference_id,
    }
    if description is not None:
        payload["description"] = description
    return client.post(f"/accounts/{account_id}/transactions", json=payload)


def test_credit_increases_balance(client):
    account = _account(client)
    response = _txn(client, account["id"], "credit", "50.00", "c-1")
    assert response.status_code == 201
    balance = client.get(f"/accounts/{account['id']}/balance").json()
    assert balance["balance"] == "50.00"


def test_debit_decreases_balance(client):
    account = _account(client)
    _txn(client, account["id"], "credit", "100.00", "c-1")
    response = _txn(client, account["id"], "debit", "30.00", "d-1")
    assert response.status_code == 201
    balance = client.get(f"/accounts/{account['id']}/balance").json()
    assert balance["balance"] == "70.00"


def test_debit_rejected_when_insufficient(client):
    account = _account(client)
    _txn(client, account["id"], "credit", "100.00", "c-1")
    response = _txn(client, account["id"], "debit", "150.00", "d-1")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INSUFFICIENT_BALANCE"
    balance = client.get(f"/accounts/{account['id']}/balance").json()
    assert balance["balance"] == "100.00"


def test_duplicate_reference_does_not_change_balance(client):
    account = _account(client)
    first = _txn(client, account["id"], "credit", "40.00", "same-ref")
    second = _txn(client, account["id"], "credit", "40.00", "same-ref")
    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "DUPLICATE_TRANSACTION"
    assert second.json()["error"]["details"]["existing_transaction"]["id"] == first.json()["id"]
    balance = client.get(f"/accounts/{account['id']}/balance").json()
    assert balance["balance"] == "40.00"


def test_same_reference_allowed_on_different_accounts(client):
    a = _account(client, "A")
    b = _account(client, "B")
    first = _txn(client, a["id"], "credit", "10.00", "shared-ref")
    second = _txn(client, b["id"], "credit", "15.00", "shared-ref")
    assert first.status_code == 201
    assert second.status_code == 201


def test_transaction_on_missing_account(client):
    response = _txn(client, "does-not-exist", "credit", "10.00", "r1")
    assert response.status_code == 404


def test_invalid_type_and_amount(client):
    account = _account(client)
    bad_type = _txn(client, account["id"], "refund", "10.00", "r1")
    assert bad_type.status_code == 400
    bad_amount = _txn(client, account["id"], "credit", "0", "r2")
    assert bad_amount.status_code == 400


def test_history_filter_pagination_and_sort(client):
    account = _account(client)
    _txn(client, account["id"], "credit", "100.00", "c-1", "first")
    _txn(client, account["id"], "credit", "50.00", "c-2", "second")
    _txn(client, account["id"], "debit", "30.00", "d-1", "third")
    _txn(client, account["id"], "debit", "20.00", "d-2", "fourth")

    latest = client.get(f"/accounts/{account['id']}/transactions").json()
    assert latest["pagination"]["total_records"] == 4
    assert [item["reference_id"] for item in latest["transactions"]] == [
        "d-2",
        "d-1",
        "c-2",
        "c-1",
    ]

    credits = client.get(
        f"/accounts/{account['id']}/transactions", params={"type": "credit"}
    ).json()
    assert credits["pagination"]["total_records"] == 2
    assert all(item["type"] == "credit" for item in credits["transactions"])

    page = client.get(
        f"/accounts/{account['id']}/transactions", params={"page": 2, "limit": 2}
    ).json()
    assert page["pagination"] == {
        "page": 2,
        "limit": 2,
        "total_records": 4,
        "total_pages": 2,
    }
    assert [item["reference_id"] for item in page["transactions"]] == ["c-2", "c-1"]


def test_invalid_pagination(client):
    account = _account(client)
    response = client.get(f"/accounts/{account['id']}/transactions", params={"page": 0})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_PAGINATION"


def test_balance_matches_transaction_sequence(client):
    account = _account(client)
    _txn(client, account["id"], "credit", "100.00", "c-1")
    _txn(client, account["id"], "credit", "50.00", "c-2")
    _txn(client, account["id"], "debit", "30.00", "d-1")
    _txn(client, account["id"], "debit", "20.00", "d-2")
    balance = client.get(f"/accounts/{account['id']}/balance").json()
    assert balance["balance"] == "100.00"


def test_transactions_cannot_be_updated_or_deleted(client):
    account = _account(client)
    _txn(client, account["id"], "credit", "10.00", "c-1")
    collection = f"/accounts/{account['id']}/transactions"
    assert client.put(collection, json={"amount": "1.00"}).status_code == 405
    assert client.patch(collection, json={"amount": "1.00"}).status_code == 405
    assert client.delete(collection).status_code == 405
