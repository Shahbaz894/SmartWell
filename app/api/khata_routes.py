# app/api/khata_routes.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.khata_schema import KhataCreate, KhataUpdate, KhataPayment, KhataResponse
from app.services.khata_service import KhataService
from app.core.logger import logger
from app.core.exceptions import AppException, NotFoundException
from typing import List

router = APIRouter(prefix="/khata", tags=["Khata"])

# Hardcoded for now — replace with JWT auth dependency later
TEMP_USER_ID = "some-user-id"


# ─────────────────────────────────────────────
# CREATE
# ─────────────────────────────────────────────
@router.post("/", response_model=KhataResponse, status_code=201)
def create_entry(data: KhataCreate, db: Session = Depends(get_db)):
    """
    Create a new khata entry.
    - run_hours auto-calculated from motor_log_id if not provided
    - total_bill auto-calculated from run_hours * price_per_hour
    - balance = total_bill - cash_received
    - is_cleared = True if balance <= 0 (entry stays visible)
    """
    service = KhataService(db)
    try:
        entry = service.create_entry(user_id=TEMP_USER_ID, data=data.dict())
        logger.info(
            "Khata entry created: customer=%s, total_bill=%s, balance=%s, is_cleared=%s",
            entry.customer_name,
            entry.total_bill,
            entry.balance,
            entry.is_cleared
        )
        return entry

    except AppException as e:
        logger.error("Failed to create khata entry: customer=%s, error=%s", data.customer_name, str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Unexpected error creating khata entry: customer=%s, error=%s", data.customer_name, str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


# ─────────────────────────────────────────────
# GET ALL
# ─────────────────────────────────────────────
@router.get("/", response_model=List[KhataResponse])
def get_all_entries(db: Session = Depends(get_db)):
    """
    Get all khata entries for the current user.
    Cleared entries remain visible with is_cleared=True.
    """
    service = KhataService(db)
    try:
        entries = service.get_all_entries(user_id=TEMP_USER_ID)
        logger.info("Fetched %d khata entries for user=%s", len(entries), TEMP_USER_ID)
        return entries

    except AppException as e:
        logger.error("Failed to fetch khata entries: %s", str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Unexpected error fetching khata entries: %s", str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


# ─────────────────────────────────────────────
# GET ONE
# ─────────────────────────────────────────────
@router.get("/{entry_id}", response_model=KhataResponse)
def get_entry(entry_id: str, db: Session = Depends(get_db)):
    """
    Get a single khata entry by ID.
    """
    service = KhataService(db)
    try:
        entry = service.get_entry(entry_id)
        return entry

    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except AppException as e:
        logger.error("Failed to fetch khata entry id=%s: %s", entry_id, str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Unexpected error fetching khata entry id=%s: %s", entry_id, str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


# ─────────────────────────────────────────────
# UPDATE  (general field update)
# ─────────────────────────────────────────────
@router.patch("/{entry_id}", response_model=KhataResponse)
def update_entry(entry_id: str, data: KhataUpdate, db: Session = Depends(get_db)):
    """
    Update allowed fields on an existing entry.
    balance and is_cleared are auto-recalculated after update.
    """
    service = KhataService(db)
    try:
        entry = service.get_entry(entry_id)
        updated = service.repo.update_entry(
            entry,
            data.dict(exclude_none=True)  # only send fields that were actually provided
        )
        logger.info(
            "Khata entry updated: id=%s, balance=%s, is_cleared=%s",
            entry_id,
            updated.balance,
            updated.is_cleared
        )
        return updated

    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except AppException as e:
        logger.error("Failed to update khata entry id=%s: %s", entry_id, str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Unexpected error updating khata entry id=%s: %s", entry_id, str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


# ─────────────────────────────────────────────
# PAY  (add payment — entry stays visible after clearing)
# ─────────────────────────────────────────────
@router.patch("/{entry_id}/pay", response_model=KhataResponse)
def update_payment(entry_id: str, data: KhataPayment, db: Session = Depends(get_db)):
    """
    Add a payment to an existing entry.
    - Adds cash_received to existing amount
    - Recalculates balance
    - Sets is_cleared=True if balance <= 0
    - Entry stays visible after clearing (is_cleared is just a flag)
    """
    service = KhataService(db)
    try:
        entry = service.update_payment(entry_id, data.cash_received)
        logger.info(
            "Payment updated: id=%s, cash_received=%s, balance=%s, is_cleared=%s",
            entry_id,
            data.cash_received,
            entry.balance,
            entry.is_cleared
        )
        return entry

    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except AppException as e:
        logger.error("Failed to update payment for entry id=%s: %s", entry_id, str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Unexpected error updating payment for entry id=%s: %s", entry_id, str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


# ─────────────────────────────────────────────
# DELETE  (only allowed when is_cleared=True)
# ─────────────────────────────────────────────
@router.delete("/{entry_id}", status_code=200)
def delete_entry(entry_id: str, db: Session = Depends(get_db)):
    """
    Delete a khata entry.
    Only allowed when entry is fully cleared (balance == 0).
    Cleared entries are NOT auto-deleted — explicit DELETE required.
    """
    service = KhataService(db)
    try:
        service.delete_entry(entry_id)
        logger.info("Khata entry deleted: id=%s", entry_id)
        return {"detail": "Entry deleted successfully"}

    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except AppException as e:
        logger.error("Failed to delete khata entry id=%s: %s", entry_id, str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Unexpected error deleting khata entry id=%s: %s", entry_id, str(e))
        raise HTTPException(status_code=500, detail="Internal server error")