from fastapi import Depends, logger
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from passlib.context import CryptContext

from app.db.session import get_db
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.core.exceptions import AppException, NotFoundException, UnauthorizedAccess
from app.services.jwt_handler import JWTHandler


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")



class AuthService:

    def __init__(self, db: Session):
        self.repo = UserRepository(db)

    # ───────── PASSWORD ─────────
    def _hash(self, password: str) -> str:
        return pwd_context.hash(password)

    def _verify(self, plain: str, hashed: str) -> bool:
        return pwd_context.verify(plain, hashed)

    # ───────── REGISTER ─────────
    def register_user(self, name: str, email: str, password: str, role: str = "user"):

        try:
            # ⚠️ SAFE CHECK (repo might raise OR return None)
            try:
                existing = self.repo.get_user_by_email(email)
            except NotFoundException:
                existing = None

            if existing:
                raise AppException(400, "Email already registered")

            # 🔐 SECURITY RULE: only backend can assign admin
            if role not in ["user", "admin"]:
                role = "user"

            user = User(
                name=name,
                email=email,
                password_hash=self._hash(password),
                role=role,
            )

            return self.repo.create_user(user)

        except SQLAlchemyError:
            raise AppException(500, "Database error during registration")

    # ───────── LOGIN ─────────
    def login(self, email: str, password: str):

        try:
            user = self.repo.get_user_by_email(email)

            if not user:
                raise NotFoundException(detail="User not found")

            if not self._verify(password, user.password_hash):
                raise AppException(401, "Incorrect credentials")

            token = JWTHandler.create_token(user)

            return {
                "access_token": token,
                "token_type": "bearer",
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "name": user.name,
                    "role": user.role,
                }
            }

        except (AppException, NotFoundException):
            raise

        except SQLAlchemyError:
            raise AppException(500, "Database error during login")
        
        
    
