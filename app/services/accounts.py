from sqlalchemy.orm import Session

from app.exceptions import AccountNotFoundError
from app.models import Account, new_id, utcnow
from app.schemas import AccountCreate


def create_account(db: Session, payload: AccountCreate) -> Account:
    account = Account(
        id=new_id(),
        name=payload.name,
        balance=0,
        created_at=utcnow(),
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def get_account_or_404(db: Session, account_id: str) -> Account:
    account = db.get(Account, account_id)
    if account is None:
        raise AccountNotFoundError(account_id)
    return account
