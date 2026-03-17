# app/api/auth_routes.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.user_schema import UserCreate, UserLogin
from app.services.auth_service import AuthService
from app.core.logger import logger
from app.core.exceptions import AppException

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    service = AuthService(db)
    try:
        created_user = service.register_user(
            name=user.name,
            email=user.email,
            password=user.password
        )
        logger.info("User registered successfully: email=%s", user.email)
        return {"id": created_user.id, "email": created_user.email, "name": created_user.name}

    except AppException as e:
        logger.error("Registration failed for email=%s: %s", user.email, str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Unexpected error during registration for email=%s: %s", user.email, str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    service = AuthService(db)
    try:
        logged_in_user = service.login(
            email=user.email,
            password=user.password
        )
        if not logged_in_user:
            logger.warning("Failed login attempt: email=%s", user.email)
            raise HTTPException(status_code=401, detail="Invalid email or password")

        logger.info("User logged in successfully: email=%s", user.email)
        return {"id": logged_in_user.id, "email": logged_in_user.email, "name": logged_in_user.name}

    except AppException as e:
        logger.error("Login failed for email=%s: %s", user.email, str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Unexpected error during login for email=%s: %s", user.email, str(e))
        raise HTTPException(status_code=500, detail="Internal server error")