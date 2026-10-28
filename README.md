# Transaction Ledger API

Python/FastAPI backend for a simple transaction ledger. Clients can create accounts, post credit and debit transactions, read balances and history, and transfer money between accounts.

## Tech stack

- Python 3.11+
- FastAPI
- SQLAlchemy 2.0
- SQLite (default, no extra services required)

Money is stored as `NUMERIC(18, 2)` and returned as decimal strings (for example `"100.00"`) to avoid floating-point rounding issues.

## Run locally

```powershell
cd C:\Users\JITENDRA\Desktop\Confluencr
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API listens on `http://127.0.0.1:8000`.

- Interactive OpenAPI docs: `http://127.0.0.1:8000/docs`
- ReDoc (read-only docs): `http://127.0.0.1:8000/redoc`
- Health check: `GET /health`

SQLite creates `ledger.db` in the project root on first start.

Optional environment variables (or a `.env` file):

| Variable        | Default                 | Purpose              |
|-----------------|-------------------------|----------------------|
| `DATABASE_URL`  | `sqlite:///./ledger.db` | SQLAlchemy database URL |
| `APP_NAME`      | `Transaction Ledger API`| Service name in `/health` |

## Tests

```powershell
pytest -q
```

## Project structure

```
app/
  main.py              # FastAPI application
  models.py            # SQLAlchemy models and constraints
  schemas.py           # Request/response validation
  exceptions.py        # Consistent error payloads
  routers/             # HTTP endpoints
  services/            # Business rules and atomic writes
tests/                 # API tests
API.md                 # Endpoint documentation
ASSUMPTIONS.md         # Design assumptions
```

## Design notes

- Account `id`, `created_at`, and initial `balance` are assigned by the server. Extra JSON fields such as `balance` on create are ignored.
- Credits add to balance; debits subtract. Debits with insufficient funds are rejected and leave the balance unchanged.
- `(account_id, reference_id)` is unique. A retry returns `409 DUPLICATE_TRANSACTION` with the original transaction and does not post a second entry.
- Transaction insert and balance update run in one database transaction (savepoint + commit). If either fails, neither is persisted.
- There are no update or delete transaction routes, so posted ledger entries are immutable through the API.
- Transfers debit the source and credit the destination in the same transaction. Account rows are locked in a stable id order to reduce deadlocks.

See [API.md](API.md) for request and response examples and [ASSUMPTIONS.md](ASSUMPTIONS.md) for scope decisions.
