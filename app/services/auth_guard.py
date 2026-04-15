# app/services/auth_guard.py

from fastapi import Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.services.jwt_handler import JWTHandler
from app.core.exceptions import AppException


oauth2_scheme = JWTHandler  # (only for reference if needed)


def get_current_user(token: str, db: Session):

    payload = JWTHandler.decode_token(token)

    user_id = payload.get("sub")

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise AppException(401, "User not found")

    return user


# ───────── ROLE PROTECTION ─────────
def require_role(role: str):
    def wrapper(user: User):
        if user.role != role:
            raise AppException(
                status_code=403,
                detail="Forbidden: insufficient permissions",
            )
        return user
    return wrapper