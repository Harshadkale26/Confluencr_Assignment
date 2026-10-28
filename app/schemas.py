from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.models import TransactionType


def serialize_money(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01'))}"


class AccountCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("name is required")
        return stripped


class AccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    balance: Decimal
    created_at: datetime

    @field_serializer("balance")
    def _balance(self, value: Decimal) -> str:
        return serialize_money(value)


class BalanceResponse(BaseModel):
    account_id: str
    balance: Decimal

    @field_serializer("balance")
    def _balance(self, value: Decimal) -> str:
        return serialize_money(value)


class TransactionCreate(BaseModel):
    type: TransactionType
    amount: Decimal = Field(..., gt=0, max_digits=18, decimal_places=2)
    reference_id: str = Field(..., min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=500)

    @field_validator("reference_id")
    @classmethod
    def reference_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("reference_id is required")
        return stripped

    @field_validator("description")
    @classmethod
    def description_strip(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    account_id: str
    type: str
    amount: Decimal
    description: str | None
    reference_id: str
    created_at: datetime

    @field_serializer("amount")
    def _amount(self, value: Decimal) -> str:
        return serialize_money(value)


class PaginationMeta(BaseModel):
    page: int
    limit: int
    total_records: int
    total_pages: int


class TransactionHistoryResponse(BaseModel):
    account_id: str
    pagination: PaginationMeta
    transactions: list[TransactionResponse]


class TransferCreate(BaseModel):
    source_account_id: str = Field(..., min_length=1)
    destination_account_id: str = Field(..., min_length=1)
    amount: Decimal = Field(..., gt=0, max_digits=18, decimal_places=2)
    reference_id: str = Field(..., min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=500)

    @field_validator("source_account_id", "destination_account_id", "reference_id")
    @classmethod
    def not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("value is required")
        return stripped


class TransferResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_account_id: str
    destination_account_id: str
    amount: Decimal
    description: str | None
    reference_id: str
    debit_transaction_id: str
    credit_transaction_id: str
    created_at: datetime

    @field_serializer("amount")
    def _amount(self, value: Decimal) -> str:
        return serialize_money(value)


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
