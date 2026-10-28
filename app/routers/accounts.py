from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import AccountCreate, AccountResponse, BalanceResponse
from app.services.accounts import create_account, get_account_or_404

router = APIRouter(prefix="/accounts", tags=["Accounts"])


@router.post("", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
def create_account_endpoint(
    payload: AccountCreate, db: Session = Depends(get_db)
) -> AccountResponse:
    account = create_account(db, payload)
    return AccountResponse.model_validate(account)


@router.get("/{account_id}", response_model=AccountResponse)
def get_account_endpoint(account_id: str, db: Session = Depends(get_db)) -> AccountResponse:
    account = get_account_or_404(db, account_id)
    return AccountResponse.model_validate(account)


@router.get("/{account_id}/balance", response_model=BalanceResponse)
def get_account_balance(account_id: str, db: Session = Depends(get_db)) -> BalanceResponse:
    account = get_account_or_404(db, account_id)
    return BalanceResponse(account_id=account.id, balance=account.balance)
