from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.exceptions import AppException, NotFoundException
from app.db.session import get_db
from app.schemas.user_schema import UserResponse
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


def handle_error(exc: Exception):
    if isinstance(exc, NotFoundException):
        raise HTTPException(status_code=404, detail=str(exc))

    if isinstance(exc, AppException):
        raise HTTPException(
            status_code=getattr(exc, "status_code", 500),
            detail=getattr(exc, "detail", str(exc)),
        )

    raise HTTPException(status_code=500, detail=str(exc))


@router.get("/", response_model=List[UserResponse])
def get_users(db: Session = Depends(get_db)):
    try:
        service = UserService(db)
        return service.get_all_users()
    except Exception as exc:
        handle_error(exc)


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: str, db: Session = Depends(get_db)):
    try:
        service = UserService(db)
        return service.get_user_by_id(user_id)
    except Exception as exc:
        handle_error(exc)


@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
def delete_user(user_id: str, db: Session = Depends(get_db)):
    try:
        service = UserService(db)
        service.delete_user(user_id)

        return {
            "message": "User deleted successfully",
            "user_id": user_id,
        }
    except Exception as exc:
        handle_error(exc)