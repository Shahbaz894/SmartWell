# app/api/khata_routes.py
#
# FastAPI router for Khata (ledger) endpoints.
#
# Base prefix  : /khata
# Auth         : JWT Bearer token required on every endpoint.
# Ownership    : customer_id on KhataEntry is ALWAYS the authenticated user's
#                ID — it is never accepted from the request body.
#
# Endpoint summary
# ────────────────
#  POST   /khata/            Create a new entry
#  GET    /khata/            List all entries for the current user
#  GET    /khata/{entry_id}  Fetch a single entry
#  PATCH  /khata/{entry_id}  Update entry fields (manual correction)
#  POST   /khata/{entry_id}/payment  Record an additional payment
#  DELETE /khata/{entry_id}  Delete a fully-cleared entry

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.auth_service import get_current_user         # returns authenticated User object
from app.core.exceptions import AppException, NotFoundException
from app.schemas.khata_schema import (
    KhataCreate,
    KhataUpdate,
    KhataPayment,
    KhataResponse,
)
from app.services.khata_service import KhataService

router = APIRouter(prefix="/khata", tags=["Accounting"])


# ── Helper: resolve service ───────────────────────────────────────────────────

def _get_service(db: Session = Depends(get_db)) -> KhataService:
    """Dependency that constructs KhataService with the current DB session."""
    return KhataService(db)


# ─────────────────────────────────────────────────────────────────────────────
# CREATE
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/",
    response_model=KhataResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Khata entry",
    description=(
        "Records a billing entry for a water consumer. "
        "run_hours is derived automatically from a linked MotorLog if not "
        "supplied manually. customer_id is always set from the JWT token."
    ),
)
def create_entry(
    body    : KhataCreate,
    current_user = Depends(get_current_user),
    service : KhataService = Depends(_get_service),
):
    """
    Create a Khata entry for the authenticated tube-well owner.

    - Validates that the device belongs to the caller.
    - Derives run_hours from motor_log if not provided.
    - Calculates total_bill, balance, and is_cleared.
    """
    return service.create_entry(
        user_id=current_user.id,
        data=body.model_dump(),           # customer_id stripped inside service
    )


# ─────────────────────────────────────────────────────────────────────────────
# LIST
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "/",
    response_model=list[KhataResponse],
    summary="Get all Khata entries",
    description=(
        "Returns every entry for the authenticated user, newest first. "
        "Cleared entries remain visible (is_cleared=True)."
    ),
)
def get_all_entries(
    current_user = Depends(get_current_user),
    service      : KhataService = Depends(_get_service),
):
    """List all ledger entries owned by the authenticated user."""
    return service.get_all_entries(user_id=current_user.id)


# ─────────────────────────────────────────────────────────────────────────────
# GET ONE
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "/{entry_id}",
    response_model=KhataResponse,
    summary="Get a single Khata entry",
)
def get_entry(
    entry_id     : str,
    current_user = Depends(get_current_user),
    service      : KhataService = Depends(_get_service),
):
    """Fetch a single Khata entry. Returns 404 if not found or not owned."""
    return service.get_entry(entry_id=entry_id, user_id=current_user.id)


# ─────────────────────────────────────────────────────────────────────────────
# UPDATE ENTRY  (general field corrections)
# ─────────────────────────────────────────────────────────────────────────────
@router.patch(
    "/{entry_id}",
    response_model=KhataResponse,
    summary="Update Khata entry fields",
    description=(
        "Allows manual correction of billing fields "
        "(customer_name, run_hours, price_per_hour, total_bill, cash_received, date). "
        "Balance and is_cleared are recalculated automatically."
    ),
)
def update_entry(
    entry_id     : str,
    body         : KhataUpdate,
    current_user = Depends(get_current_user),
    service      : KhataService = Depends(_get_service),
):
    """
    Apply partial field updates to a Khata entry.
    Only non-None fields in the body are changed.
    """
    return service.update_entry(
        entry_id=entry_id,
        user_id=current_user.id,
        data=body.model_dump(exclude_none=True),
    )


# ─────────────────────────────────────────────────────────────────────────────
# RECORD PAYMENT  (additive)
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/{entry_id}/payment",
    response_model=KhataResponse,
    summary="Record a payment on an entry",
    description=(
        "Adds the supplied cash_received amount to the existing balance. "
        "Once the balance reaches zero, is_cleared is set to True. "
        "Cleared entries remain visible until explicitly deleted."
    ),
)
def update_payment(
    entry_id     : str,
    body         : KhataPayment,
    current_user = Depends(get_current_user),
    service      : KhataService = Depends(_get_service),
):
    """Record an additional payment. Raises 400 if already cleared."""
    return service.update_payment(
        entry_id=entry_id,
        user_id=current_user.id,
        cash_received=body.cash_received,
    )


# ─────────────────────────────────────────────────────────────────────────────
# DELETE  (only when fully cleared)
# ─────────────────────────────────────────────────────────────────────────────
@router.delete(
    "/{entry_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a cleared Khata entry",
    description=(
        "Permanently removes a Khata entry from the database. "
        "Deletion is only permitted after the entry is fully cleared "
        "(is_cleared=True / balance=0). "
        "Call the /payment endpoint first to settle any outstanding balance."
    ),
)
def delete_entry(
    entry_id     : str,
    current_user = Depends(get_current_user),
    service      : KhataService = Depends(_get_service),
):
    """
    Hard-delete a cleared Khata entry.

    Returns 400 if the balance is still pending.
    Returns 404 if the entry is not found or not owned by the caller.
    """
    service.delete_entry(entry_id=entry_id, user_id=current_user.id)
    return {"detail": "Entry successfully deleted", "entry_id": entry_id}