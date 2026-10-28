from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import TransferCreate, TransferResponse
from app.services.transfers import create_transfer

router = APIRouter(prefix="/transfers", tags=["Transfers"])


@router.post("", response_model=TransferResponse, status_code=status.HTTP_201_CREATED)
def transfer_money(
    payload: TransferCreate, db: Session = Depends(get_db)
) -> TransferResponse:
    transfer = create_transfer(db, payload)
    return TransferResponse.model_validate(transfer)
