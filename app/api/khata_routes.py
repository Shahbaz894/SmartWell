# app/api/khata_routes.py
#
# FastAPI router for Khata (ledger) endpoints.
#
# Base prefix  : /khata
# Auth         : JWT Bearer token required on every endpoint.
# Ownership    : user_id on KhataEntry is ALWAYS the authenticated user's
#                ID — it is never accepted from the request body.
#
# IMPORTANT: current_user.id is always wrapped in str() before being passed
# to the service layer. The User model may store id as a uuid.UUID object
# (UUID(as_uuid=True)), which causes a PostgreSQL type error when compared
# against String columns on KhataEntry. str() normalises this everywhere.
#
# Endpoint summary
# ────────────────
#  GET    /khata/me                   Debug: return current user info
#  POST   /khata/                     Create a new entry
#  GET    /khata/                     List all entries for current user
#  GET    /khata/{entry_id}           Fetch a single entry
#  PATCH  /khata/{entry_id}           Update entry fields
#  POST   /khata/{entry_id}/payment   Record an additional payment
#  DELETE /khata/{entry_id}           Delete a fully-cleared entry

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_user
from app.schemas.khata_schema import (
    KhataCreate,
    KhataUpdate,
    KhataPayment,
    KhataResponse,
)
from app.services.khata_service import KhataService

router = APIRouter(prefix="/khata", tags=["Accounting"])


# ─────────────────────────────────────────────────────────────────────────────
# DEPENDENCY
# ─────────────────────────────────────────────────────────────────────────────

def _get_service(db: Session = Depends(get_db)) -> KhataService:
    """Construct KhataService with the current DB session."""
    return KhataService(db)


# ─────────────────────────────────────────────────────────────────────────────
# DEBUG — /khata/me
# NOTE: Declared BEFORE /{entry_id} routes to prevent FastAPI treating
#       "me" as an entry_id path parameter.
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/me",
    summary="Return current authenticated user info",
    description="Verify JWT token validity and identify the caller.",
)
def get_me(current_user=Depends(get_current_user)):
    """Return user_id and email of the authenticated caller."""
    return {
        "user_id": str(current_user.id),
        "email":   current_user.email,
    }


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
        "supplied manually. user_id is always taken from the JWT token."
    ),
)
def create_entry(
    body         : KhataCreate,
    current_user = Depends(get_current_user),
    service      : KhataService = Depends(_get_service),
):
    """
    Create a Khata entry for the authenticated tube-well owner.

    - Validates device ownership.
    - Derives run_hours from motor_log if not provided directly.
    - Computes total_bill, balance, and is_cleared server-side.
    """
    return service.create_entry(
        user_id = str(current_user.id),   # str() — guard against uuid.UUID object
        data    = body.model_dump(),
    )


# ─────────────────────────────────────────────────────────────────────────────
# LIST
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/",
    response_model=list[KhataResponse],
    summary="List all Khata entries",
    description="Returns every entry for the authenticated user, newest first.",
)
def get_all_entries(
    current_user = Depends(get_current_user),
    service      : KhataService = Depends(_get_service),
):
    """List all ledger entries owned by the authenticated user."""
    return service.get_all_entries(
        user_id = str(current_user.id),   # str() — guard against uuid.UUID object
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET ONE
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/{entry_id}",
    response_model=KhataResponse,
    summary="Get a single Khata entry",
    description="Returns 404 if the entry does not exist or is not owned by the caller.",
)
def get_entry(
    entry_id     : str,
    current_user = Depends(get_current_user),
    service      : KhataService = Depends(_get_service),
):
    """Fetch a single Khata entry by ID."""
    return service.get_entry(
        entry_id = str(entry_id),
        user_id  = str(current_user.id),  # str() — guard against uuid.UUID object
    )


# ─────────────────────────────────────────────────────────────────────────────
# UPDATE
# ─────────────────────────────────────────────────────────────────────────────

@router.patch(
    "/{entry_id}",
    response_model=KhataResponse,
    summary="Update Khata entry fields",
    description=(
        "Partially update billing fields. "
        "balance and is_cleared are recalculated automatically after update."
    ),
)
def update_entry(
    entry_id     : str,
    body         : KhataUpdate,
    current_user = Depends(get_current_user),
    service      : KhataService = Depends(_get_service),
):
    """Apply partial field corrections to an existing Khata entry."""
    return service.update_entry(
        entry_id = str(entry_id),
        user_id  = str(current_user.id),
        data     = body.model_dump(exclude_none=True),
    )


# ─────────────────────────────────────────────────────────────────────────────
# PAYMENT
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/{entry_id}/payment",
    response_model=KhataResponse,
    summary="Record a payment on an entry",
    description=(
        "Adds cash_received to the running total. "
        "Sets is_cleared=True once balance reaches zero."
    ),
)
def update_payment(
    entry_id     : str,
    body         : KhataPayment,
    current_user = Depends(get_current_user),
    service      : KhataService = Depends(_get_service),
):
    """Record an incremental payment. Returns 400 if already cleared."""
    return service.update_payment(
        entry_id      = str(entry_id),
        user_id       = str(current_user.id),
        cash_received = body.cash_received,
    )


# ─────────────────────────────────────────────────────────────────────────────
# DELETE
# ─────────────────────────────────────────────────────────────────────────────

@router.delete(
    "/{entry_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a cleared Khata entry",
    description=(
        "Permanently removes a Khata entry. "
        "Only permitted when is_cleared=True (balance=0). "
        "Use the /payment endpoint first to settle any outstanding balance."
    ),
)
def delete_entry(
    entry_id     : str,
    current_user = Depends(get_current_user),
    service      : KhataService = Depends(_get_service),
):
    """
    Hard-delete a cleared entry.

    Returns 400 if balance is still pending.
    Returns 404 if not found or not owned by caller.
    """
    service.delete_entry(
        entry_id = str(entry_id),
        user_id  = str(current_user.id),
    )
    return {"detail": "Entry successfully deleted", "entry_id": entry_id}