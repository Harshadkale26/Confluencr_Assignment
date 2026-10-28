# API Documentation

Base URL (local): `http://127.0.0.1:8000`

All successful money fields are JSON strings with two decimal places (example: `"70.00"`).

Error body (all failures):

```json
{
  "error": {
    "code": "ACCOUNT_NOT_FOUND",
    "message": "Account 'abc' was not found.",
    "details": {}
  }
}
```

`details` is omitted when empty. Validation failures use `code: "INVALID_REQUEST"` and HTTP `400`.

| HTTP | Typical codes |
|------|----------------|
| 201  | Resource created |
| 200  | Read success |
| 400  | Invalid body or pagination |
| 404  | Account not found |
| 409  | Duplicate transaction or transfer |
| 422  | Insufficient balance |
| 405  | Method not allowed (no edit/delete on transactions) |

---

## Health

`GET /health`

```json
{ "status": "ok", "service": "Transaction Ledger API" }
```

---

## Create account

`POST /accounts`

Request:

```json
{ "name": "Ada Lovelace" }
```

`name` is required and cannot be blank. `balance` cannot be set by the client.

Response `201`:

```json
{
  "id": "3d2c1a4e-....",
  "name": "Ada Lovelace",
  "balance": "0.00",
  "created_at": "2026-10-27T19:00:00.000000+00:00"
}
```

---

## Get account

`GET /accounts/{account_id}`

Response `200`: same shape as create. `404` if the id does not exist.

---

## Get account balance

`GET /accounts/{account_id}/balance`

Response `200`:

```json
{
  "account_id": "3d2c1a4e-....",
  "balance": "100.00"
}
```

---

## Add transaction

`POST /accounts/{account_id}/transactions`

Request:

```json
{
  "type": "credit",
  "amount": "50.00",
  "reference_id": "inv-1001",
  "description": "Invoice payment"
}
```

Rules:

- `type` must be `credit` or `debit`
- `amount` must be greater than `0` (max 18 digits, 2 decimal places)
- `reference_id` is required
- `description` is optional
- Credit increases balance; debit decreases it
- Debit with insufficient funds → `422 INSUFFICIENT_BALANCE` (balance unchanged)
- Unknown account → `404 ACCOUNT_NOT_FOUND`
- Same `reference_id` on the same account → `409 DUPLICATE_TRANSACTION` (no new row, balance unchanged). The existing transaction is returned under `error.details.existing_transaction`
- The same `reference_id` may be used on a different account

Response `201`:

```json
{
  "id": "9f8e....",
  "account_id": "3d2c1a4e-....",
  "type": "credit",
  "amount": "50.00",
  "description": "Invoice payment",
  "reference_id": "inv-1001",
  "created_at": "2026-10-27T19:01:00.000000+00:00"
}
```

There is no `PUT`, `PATCH`, or `DELETE` for transactions.

---

## Transaction history

`GET /accounts/{account_id}/transactions`

Query parameters:

| Name   | Default | Notes |
|--------|---------|--------|
| `type` | omitted | `credit` or `debit`. If omitted, both are returned |
| `page` | `1`     | Must be ≥ 1 |
| `limit`| `20`    | Must be 1–100 |

Sort: `created_at` descending (latest first), then `id` descending for a stable order.

Response `200`:

```json
{
  "account_id": "3d2c1a4e-....",
  "pagination": {
    "page": 1,
    "limit": 20,
    "total_records": 4,
    "total_pages": 1
  },
  "transactions": []
}
```

Invalid `page` / `limit` → `400 INVALID_PAGINATION`. Missing account → `404`.

---

## Transfer money (bonus)

`POST /transfers`

Request:

```json
{
  "source_account_id": "account-a",
  "destination_account_id": "account-b",
  "amount": "30.00",
  "reference_id": "rent-2026-10",
  "description": "October rent"
}
```

Effects (atomic):

1. Debit source by `amount` (`reference_id` stored as `{reference_id}:debit`)
2. Credit destination by `amount` (`{reference_id}:credit`)
3. Persist a transfer record linking both ledger entries

If any step fails, nothing is committed.

Response `201` includes `id`, both account ids, `amount`, `reference_id`, `debit_transaction_id`, `credit_transaction_id`, and `created_at`.

Failures:

- Same source and destination → `400 SAME_ACCOUNT_TRANSFER`
- Missing account → `404 ACCOUNT_NOT_FOUND`
- Source cannot cover `amount` → `422 INSUFFICIENT_BALANCE`
- Reused transfer `reference_id` → `409 DUPLICATE_TRANSFER`
