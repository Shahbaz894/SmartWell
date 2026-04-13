# app/services/auth_service.py

from passlib.context import CryptContext
from sqlalchemy.exc import SQLAlchemyError
from app.repositories.user_repo import UserRepository
from app.models.user import User
from app.core.logger import logger
from app.core.exceptions import AppException, NotFoundException

# --- ADDED IMPORTS FOR get_current_user ---
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from app.db.session import get_db # Ensure this path matches your project
from sqlalchemy.orm import Session
# ------------------------------------------

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# This tells FastAPI where to look for the token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login") 

class AuthService:
    def __init__(self, db):
        self.user_repo = UserRepository(db)

    def hash_password(self, password: str):
        return pwd_context.hash(password)

    def verify_password(self, plain, hashed):
        return pwd_context.verify(plain, hashed)

    def register_user(self, name, email, password):
        try:
            hashed = self.hash_password(password)
            user = User(
                name=name,
                email=email,
                password_hash=hashed
            )
            created_user = self.user_repo.create_user(user)
            logger.info("User registered: id=%s, email=%s", created_user.id, created_user.email)
            return created_user
        except SQLAlchemyError as e:
            logger.error("Failed to register user %s: %s", email, str(e))
            raise AppException(f"Database error: failed to register user {email}")

    def login(self, email, password):
        try:
            user = self.user_repo.get_user_by_email(email)
            if not user:
                logger.warning("Login failed: user not found with email %s", email)
                raise NotFoundException(f"User with email {email} not found")

            if not self.verify_password(password, user.password_hash):
                logger.warning("Login failed: invalid password for email %s", email)
                return None

            logger.info("User logged in successfully: email=%s", email)
            return user
        except SQLAlchemyError as e:
            logger.error("Failed during login for email %s: %s", email, str(e))
            raise AppException(f"Database error during login for user {email}")

# --- ADDED FUNCTION TO FIX IMPORT ERROR ---
async def get_current_user(
    token: str = Depends(oauth2_scheme), 
    db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Use your actual SECRET_KEY and ALGORITHM here
        payload = jwt.decode(token, "your_secret_key_here", algorithms=["HS256"])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user_repo = UserRepository(db)
    user = user_repo.get_user_by_email(email)
    
    if user is None:
        raise credentials_exception
    return user