from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import TransactionType
from app.schemas import (
    PaginationMeta,
    TransactionCreate,
    TransactionHistoryResponse,
    TransactionResponse,
)
from app.services.transactions import add_transaction, list_transactions, total_pages

router = APIRouter(prefix="/accounts/{account_id}/transactions", tags=["Transactions"])


@router.post("", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
def create_transaction(
    account_id: str, payload: TransactionCreate, db: Session = Depends(get_db)
) -> TransactionResponse:
    transaction = add_transaction(db, account_id, payload)
    return TransactionResponse.model_validate(transaction)


@router.get("", response_model=TransactionHistoryResponse)
def get_transaction_history(
    account_id: str,
    db: Session = Depends(get_db),
    type: TransactionType | None = Query(default=None),
    page: int = Query(default=1),
    limit: int = Query(default=20),
) -> TransactionHistoryResponse:
    items, total = list_transactions(db, account_id, type, page, limit)
    return TransactionHistoryResponse(
        account_id=account_id,
        pagination=PaginationMeta(
            page=page,
            limit=limit,
            total_records=total,
            total_pages=total_pages(total, limit),
        ),
        transactions=[TransactionResponse.model_validate(item) for item in items],
    )
