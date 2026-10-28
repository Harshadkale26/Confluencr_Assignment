from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions import (
    AccountNotFoundError,
    DuplicateTransferError,
    InsufficientBalanceError,
    SameAccountTransferError,
)
from app.models import Account, Transaction, TransactionType, Transfer, new_id, utcnow
from app.schemas import TransferCreate, TransferResponse


def _lock_accounts(db: Session, first_id: str, second_id: str) -> tuple[Account, Account]:
    ordered = sorted({first_id, second_id})
    accounts = {
        account.id: account
        for account in db.execute(
            select(Account).where(Account.id.in_(ordered)).with_for_update()
        )
        .scalars()
        .all()
    }
    missing = [account_id for account_id in ordered if account_id not in accounts]
    if missing:
        raise AccountNotFoundError(missing[0])
    return accounts[first_id], accounts[second_id]


def _to_response_dict(transfer: Transfer) -> dict:
    return TransferResponse.model_validate(transfer).model_dump(mode="json")


def create_transfer(db: Session, payload: TransferCreate) -> Transfer:
    if payload.source_account_id == payload.destination_account_id:
        raise SameAccountTransferError()

    existing = db.execute(
        select(Transfer).where(Transfer.reference_id == payload.reference_id)
    ).scalar_one_or_none()
    if existing is not None:
        raise DuplicateTransferError(_to_response_dict(existing))

    amount = payload.amount.quantize(Decimal("0.01"))
    transfer_id = new_id()
    debit_id = new_id()
    credit_id = new_id()
    now = utcnow()
    description = payload.description or f"Transfer {payload.reference_id}"

    try:
        with db.begin_nested():
            source, destination = _lock_accounts(
                db, payload.source_account_id, payload.destination_account_id
            )
            source_balance = Decimal(source.balance)
            if source_balance < amount:
                raise InsufficientBalanceError(
                    account_id=source.id,
                    balance=str(source_balance.quantize(Decimal("0.01"))),
                    amount=str(amount),
                )

            debit = Transaction(
                id=debit_id,
                account_id=source.id,
                type=TransactionType.DEBIT.value,
                amount=amount,
                description=description,
                reference_id=f"{payload.reference_id}:debit",
                created_at=now,
            )
            credit = Transaction(
                id=credit_id,
                account_id=destination.id,
                type=TransactionType.CREDIT.value,
                amount=amount,
                description=description,
                reference_id=f"{payload.reference_id}:credit",
                created_at=now,
            )
            source.balance = source_balance - amount
            destination.balance = Decimal(destination.balance) + amount

            transfer = Transfer(
                id=transfer_id,
                source_account_id=source.id,
                destination_account_id=destination.id,
                amount=amount,
                description=payload.description,
                reference_id=payload.reference_id,
                debit_transaction_id=debit_id,
                credit_transaction_id=credit_id,
                created_at=now,
            )
            db.add(debit)
            db.add(credit)
            db.flush()
            db.add(transfer)
            db.flush()
    except IntegrityError:
        db.rollback()
        existing = db.execute(
            select(Transfer).where(Transfer.reference_id == payload.reference_id)
        ).scalar_one_or_none()
        if existing is not None:
            raise DuplicateTransferError(_to_response_dict(existing)) from None
        debit_conflict = db.execute(
            select(Transaction).where(
                Transaction.account_id == payload.source_account_id,
                Transaction.reference_id == f"{payload.reference_id}:debit",
            )
        ).scalar_one_or_none()
        if debit_conflict is not None:
            raise DuplicateTransferError(
                {
                    "message": "A ledger entry already exists for this transfer reference.",
                    "conflicting_transaction_id": debit_conflict.id,
                }
            ) from None
        raise

    db.commit()
    db.refresh(transfer)
    return transfer
