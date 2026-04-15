from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm

from app.db.session import get_db
from app.schemas.user_schema import UserCreate, UserLogin
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])


# ───────── REGISTER ─────────
@router.post("/register")
def register(body: UserCreate, db: Session = Depends(get_db)):

    service = AuthService(db)

    user = service.register_user(
        name=body.name,
        email=body.email,
        password=body.password,
        role=body.role or "user",
    )

    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
    }


# ───────── LOGIN (Flutter + Next.js) ─────────
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