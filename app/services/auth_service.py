# app/services/auth_service.py

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from passlib.context import CryptContext

from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.core.exceptions import AppException, NotFoundException
from app.services.jwt_handler import JWTHandler


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:

    def __init__(self, db: Session):
        self.repo = UserRepository(db)

    # ───────── PASSWORD ─────────
    def _hash(self, password: str) -> str:
        return pwd_context.hash(password)

    def _verify(self, plain: str, hashed: str) -> bool:
        return pwd_context.verify(plain, hashed)

    # ───────── REGISTER ─────────
    def register_user(self, name: str, email: str, password: str, role="user"):

        try:
            if self.repo.get_user_by_email(email):
                raise AppException(400, "Email already registered")

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
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "role": user.role,
                }
            }

        except (AppException, NotFoundException):
            raise

        except SQLAlchemyError:
            raise AppException(500, "Database error during login")