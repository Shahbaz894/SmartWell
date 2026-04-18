# app/core/security.py

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.services.jwt_handler import JWTHandler
from app.core.exceptions import AppException
from app.core.logger import logger

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db:    Session = Depends(get_db),
) -> User:
    """
    Validate JWT Bearer token and return the authenticated User.

    Raises:
        AppException: 401 if token is missing, invalid, expired,
                      or the user no longer exists in the DB.
    """

    # ── 1. Decode & validate token ────────────────────────────────────────────
    try:
        payload = JWTHandler.decode_token(token)
    except AppException:
        raise  # already a clean 401 — let it go
    except Exception as exc:
        logger.error("JWT decode failed: %s", repr(exc), exc_info=True)
        raise AppException(401, "Invalid or expired token")

    # ── 2. Extract subject (user_id) ──────────────────────────────────────────
    user_id = payload.get("sub")

    if not user_id:
        logger.warning("JWT payload missing 'sub' claim | payload=%s", payload)
        raise AppException(401, "Invalid token — missing subject")

    # ── 3. Load user from DB ──────────────────────────────────────────────────
    try:
        user = db.query(User).filter(User.id == user_id).first()
    except Exception as exc:
        logger.error(
            "DB error during auth | user_id=%s error=%s",
            user_id, repr(exc), exc_info=True,
        )
        raise AppException(500, "Authentication service error")

    if not user:
        logger.warning("Authenticated user_id not found in DB | user_id=%s", user_id)
        raise AppException(401, "User not found")

    logger.debug("User authenticated | user_id=%s email=%s", user.id, user.email)
    return user