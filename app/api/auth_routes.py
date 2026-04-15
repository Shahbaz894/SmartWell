# app/api/auth_routes.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.user_schema import UserCreate, UserLogin
from app.services.auth_service import AuthService
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter(prefix="/auth", tags=["Auth"])


# ───────── REGISTER ─────────
@router.post("/register")
def register(body: UserCreate, db: Session = Depends(get_db)):

    service = AuthService(db)

    user = service.register_user(
        name=body.name,
        email=body.email,
        password=body.password,
        role=getattr(body, "role", "user"),
    )

    return user


# ───────── LOGIN (FLUTTER + NEXT JS) ─────────
@router.post("/login")
def login(body: UserLogin, db: Session = Depends(get_db)):

    service = AuthService(db)

    return service.login(body.email, body.password)


# ───────── SWAGGER LOGIN ─────────
@router.post("/token")
def swagger_login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):

    service = AuthService(db)

    return service.login(
        email=form_data.username,
        password=form_data.password,
    )