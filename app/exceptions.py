from fastapi import Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class LedgerError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        http_status: int,
        details: dict | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status
        self.details = details or {}
        super().__init__(message)


class AccountNotFoundError(LedgerError):
    def __init__(self, account_id: str) -> None:
        super().__init__(
            code="ACCOUNT_NOT_FOUND",
            message=f"Account '{account_id}' was not found.",
            http_status=status.HTTP_404_NOT_FOUND,
            details={"account_id": account_id},
        )


class DuplicateTransactionError(LedgerError):
    def __init__(self, existing_transaction: dict) -> None:
        super().__init__(
            code="DUPLICATE_TRANSACTION",
            message="A transaction with this reference_id already exists for the account.",
            http_status=status.HTTP_409_CONFLICT,
            details={"existing_transaction": existing_transaction},
        )


class DuplicateTransferError(LedgerError):
    def __init__(self, existing_transfer: dict) -> None:
        super().__init__(
            code="DUPLICATE_TRANSFER",
            message="A transfer with this reference_id already exists.",
            http_status=status.HTTP_409_CONFLICT,
            details={"existing_transfer": existing_transfer},
        )


class InsufficientBalanceError(LedgerError):
    def __init__(self, account_id: str, balance: str, amount: str) -> None:
        super().__init__(
            code="INSUFFICIENT_BALANCE",
            message="The account does not have sufficient balance for this debit.",
            http_status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details={
                "account_id": account_id,
                "current_balance": balance,
                "requested_amount": amount,
            },
        )


class InvalidPaginationError(LedgerError):
    def __init__(self, message: str) -> None:
        super().__init__(
            code="INVALID_PAGINATION",
            message=message,
            http_status=status.HTTP_400_BAD_REQUEST,
        )


class SameAccountTransferError(LedgerError):
    def __init__(self) -> None:
        super().__init__(
            code="SAME_ACCOUNT_TRANSFER",
            message="Source and destination accounts must be different.",
            http_status=status.HTTP_400_BAD_REQUEST,
        )


def error_body(code: str, message: str, details: dict | None = None) -> dict:
    payload: dict = {"error": {"code": code, "message": message}}
    if details:
        payload["error"]["details"] = details
    return payload


async def ledger_error_handler(_request: Request, exc: LedgerError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.http_status,
        content=error_body(exc.code, exc.message, exc.details or None),
    )


def _serializable_errors(errors: list) -> list:
    cleaned = []
    for item in errors:
        entry = dict(item)
        ctx = entry.get("ctx")
        if isinstance(ctx, dict) and "error" in ctx:
            entry["ctx"] = {**ctx, "error": str(ctx["error"])}
        cleaned.append(entry)
    return jsonable_encoder(cleaned)


async def validation_error_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=error_body(
            "INVALID_REQUEST",
            "Request validation failed.",
            {"errors": _serializable_errors(exc.errors())},
        ),
    )
