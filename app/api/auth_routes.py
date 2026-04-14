# app/api/auth_routes.py
#
# Authentication endpoints.
#
# Base prefix : /auth
# Auth        : Register and login are public — no token required.
#
# Endpoint summary
# ────────────────
#  POST  /auth/register   Create a new user account
#  POST  /auth/login      Validate credentials → returns JWT access token

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.user_schema import UserCreate, UserLogin
from app.services.auth_service import AuthService
from app.core.logger import logger

router = APIRouter(prefix="/auth", tags=["Auth"])


# ─────────────────────────────────────────────────────────────────────────────
# REGISTER
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Creates a new tube-well owner account. Email must be unique.",
)
def register(body: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user.

    - Password is bcrypt-hashed before storage.
    - Returns basic profile info (no password hash exposed).
    - Raises 400 if the email is already registered.

    AppException is a subclass of HTTPException — FastAPI maps it to the
    correct HTTP status automatically; no manual re-wrapping needed.
    """
    service = AuthService(db)
    created = service.register_user(
        name     = body.name,
        email    = body.email,
        password = body.password,
    )
    logger.info("User registered via API: id=%s, email=%s", created.id, created.email)
    return {
        "id"    : created.id,
        "email" : created.email,
        "name"  : created.name,
    }


# ─────────────────────────────────────────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/login",
    summary="Login and receive a JWT token",
    description=(
        "Validates email + password. "
        "On success returns a Bearer token to use on all protected endpoints."
    ),
)
def login(body: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate a user and return a JWT access token.

    Response
    --------
    .. code-block:: json

        {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "token_type":   "bearer"
        }

    Use the token in the Authorization header on every protected route:

        Authorization: Bearer <access_token>

    Raises 404 if the email is not registered.
    Raises 401 if the password is incorrect.
    """
    service = AuthService(db)
    token = service.login(email=body.email, password=body.password)
    # service.login() returns {"access_token": str, "token_type": "bearer"}
    # or raises AppException(401/404) — no manual catch needed here.
    logger.info("User logged in via API: email=%s", body.email)
    return token