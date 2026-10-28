from decimal import Decimal
from math import ceil

from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions import (
    DuplicateTransactionError,
    InsufficientBalanceError,
    InvalidPaginationError,
)
from app.models import Account, Transaction, TransactionType, new_id, utcnow
from app.schemas import TransactionCreate, TransactionResponse
from app.services.accounts import get_account_or_404


def _lock_account(db: Session, account_id: str) -> Account:
    account = db.execute(
        select(Account).where(Account.id == account_id).with_for_update()
    ).scalar_one_or_none()
    if account is None:
        from app.exceptions import AccountNotFoundError

        raise AccountNotFoundError(account_id)
    return account


def _to_response_dict(transaction: Transaction) -> dict:
    return TransactionResponse.model_validate(transaction).model_dump(mode="json")


def add_transaction(db: Session, account_id: str, payload: TransactionCreate) -> Transaction:
    existing = db.execute(
        select(Transaction).where(
            Transaction.account_id == account_id,
            Transaction.reference_id == payload.reference_id,
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise DuplicateTransactionError(_to_response_dict(existing))

    try:
        with db.begin_nested():
            account = _lock_account(db, account_id)
            amount = payload.amount.quantize(Decimal("0.01"))
            current = Decimal(account.balance)

            if payload.type == TransactionType.DEBIT and current < amount:
                raise InsufficientBalanceError(
                    account_id=account_id,
                    balance=str(current.quantize(Decimal("0.01"))),
                    amount=str(amount),
                )

            if payload.type == TransactionType.CREDIT:
                account.balance = current + amount
            else:
                account.balance = current - amount

            transaction = Transaction(
                id=new_id(),
                account_id=account.id,
                type=payload.type.value,
                amount=amount,
                description=payload.description,
                reference_id=payload.reference_id,
                created_at=utcnow(),
            )
            db.add(transaction)
            db.flush()
    except IntegrityError:
        db.rollback()
        existing = db.execute(
            select(Transaction).where(
                Transaction.account_id == account_id,
                Transaction.reference_id == payload.reference_id,
            )
        ).scalar_one_or_none()
        if existing is not None:
            raise DuplicateTransactionError(_to_response_dict(existing)) from None
        raise

    db.commit()
    db.refresh(transaction)
    return transaction


def list_transactions(
    db: Session,
    account_id: str,
    transaction_type: TransactionType | None,
    page: int,
    limit: int,
) -> tuple[list[Transaction], int]:
    if page < 1:
        raise InvalidPaginationError("page must be greater than or equal to 1.")
    if limit < 1 or limit > 100:
        raise InvalidPaginationError("limit must be between 1 and 100.")

    get_account_or_404(db, account_id)

    filters = [Transaction.account_id == account_id]
    if transaction_type is not None:
        filters.append(Transaction.type == transaction_type.value)

    total = db.scalar(select(func.count()).select_from(Transaction).where(*filters)) or 0

    query: Select[tuple[Transaction]] = (
        select(Transaction)
        .where(*filters)
        .order_by(Transaction.created_at.desc(), Transaction.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    items = list(db.scalars(query).all())
    return items, int(total)


def total_pages(total_records: int, limit: int) -> int:
    if total_records == 0:
        return 0
    return ceil(total_records / limit)
