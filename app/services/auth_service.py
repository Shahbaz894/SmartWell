# app/services/auth_service.py
#
# Authentication service layer.
# Handles password hashing, user registration, login validation,
# and JWT token creation / verification.
#
# ── Design Notes ──────────────────────────────────────────────────────────────
#  • Passwords are hashed with bcrypt via passlib — plain-text is never stored.
#  • JWTs are signed with HS256 using SECRET_KEY from settings.
#  • get_current_user is a FastAPI dependency that validates the Bearer token
#    on every protected route and returns the authenticated User object.
#  • AppException is always called with (status_code=int, detail=str) —
#    never with a positional string, which would crash on __init__.
# ──────────────────────────────────────────────────────────────────────────────

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.config import settings          # must expose SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from app.core.logger import logger
from app.core.exceptions import AppException, NotFoundException
from app.db.session import get_db
from app.models.user import User
from app.repositories.user_repo import UserRepository


# ── Crypto helpers ─────────────────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# tokenUrl must match the login endpoint path registered in your router
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ── JWT helpers ────────────────────────────────────────────────────────────────

def create_access_token(subject: str) -> str:
    """
    Create a signed JWT access token.

    Parameters
    ----------
    subject : str
        The value stored in the ``sub`` claim — use the user's UUID string.

    Returns
    -------
    str
        Encoded JWT string ready to be returned in the login response.
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": subject, "exp": expire}
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    logger.debug("Access token created: sub=%s, exp=%s", subject, expire.isoformat())
    return token


def decode_access_token(token: str) -> str:
    """
    Decode and validate a JWT, returning the ``sub`` claim (user_id).

    Parameters
    ----------
    token : str
        Raw Bearer token string.

    Returns
    -------
    str
        The ``sub`` claim value (user UUID string).

    Raises
    ------
    AppException(401)
        Token is missing the ``sub`` claim, expired, or otherwise invalid.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        user_id: str = payload.get("sub")
        if not user_id:
            raise AppException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject claim",
            )
        return user_id
    except JWTError as exc:
        logger.warning("JWT decode failed: %s", exc)
        raise AppException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is invalid or has expired. Please log in again.",
        )


# ── FastAPI dependency ─────────────────────────────────────────────────────────

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI dependency — validates the Bearer JWT and returns the User.

    Attach to any route that requires authentication:

        @router.get("/protected")
        def protected(current_user: User = Depends(get_current_user)):
            ...

    Flow
    ----
    1. OAuth2PasswordBearer extracts the Bearer token from the Authorization
       header and rejects requests that have no header at all (401).
    2. decode_access_token validates the signature and expiry.
    3. The user_id from ``sub`` is used to look up the User row.
    4. Missing users (deleted accounts, stale tokens) raise 401.

    Raises
    ------
    AppException(401)
        No / invalid / expired token, or user no longer exists in DB.
    """
    user_id = decode_access_token(token)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.warning(
            "get_current_user: user_id=%s from token not found in DB", user_id
        )
        raise AppException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists. Please log in again.",
        )

    logger.debug("Authenticated user: id=%s, email=%s", user.id, user.email)
    return user


# ── Service class ──────────────────────────────────────────────────────────────

class AuthService:
    """
    Business logic for user registration and login.

    Responsibilities
    ----------------
    - Hash passwords with bcrypt before persistence.
    - Verify passwords during login without exposing hashes.
    - Delegate all DB operations to UserRepository.
    - Return JWT access tokens on successful login.
    """

    def __init__(self, db: Session):
        self.user_repo = UserRepository(db)

    # ── Internals ──────────────────────────────────────────────────────────────

    def _hash_password(self, password: str) -> str:
        """Return bcrypt hash of *password*. Never stored as plain-text."""
        return pwd_context.hash(password)

    def _verify_password(self, plain: str, hashed: str) -> bool:
        """Return True if *plain* matches *hashed*, False otherwise."""
        return pwd_context.verify(plain, hashed)

    # ── Public API ─────────────────────────────────────────────────────────────

    def register_user(self, name: str, email: str, password: str) -> User:
        """
        Register a new user with a bcrypt-hashed password.

        Parameters
        ----------
        name     : str   Display name.
        email    : str   Must be unique in the users table.
        password : str   Plain-text password supplied by the user.

        Returns
        -------
        User
            The newly created, committed User row.

        Raises
        ------
        AppException(400)
            Email already registered (unique constraint violation) or other
            database error during INSERT.
        """
        try:
            user = User(
                name          = name,
                email         = email,
                password_hash = self._hash_password(password),
            )
            created = self.user_repo.create_user(user)
            logger.info(
                "User registered: id=%s, email=%s", created.id, created.email
            )
            return created

        except SQLAlchemyError as exc:
            logger.error(
                "Failed to register user email=%s: %s", email, exc, exc_info=True
            )
            raise AppException(
                status_code=400,
                detail=f"Database error: failed to register user '{email}'. "
                       "Email may already be in use.",
            )

    def login(self, email: str, password: str) -> dict:
        """
        Validate credentials and return a JWT access token on success.

        Parameters
        ----------
        email    : str   Registered email address.
        password : str   Plain-text password to verify.

        Returns
        -------
        dict
            ``{"access_token": str, "token_type": "bearer"}``

        Raises
        ------
        NotFoundException(404)
            No user with the given email exists.
        AppException(401)
            Password does not match the stored hash.
        AppException(400)
            Database error during lookup.
        """
        try:
            user = self.user_repo.get_user_by_email(email)
            if not user:
                logger.warning(
                    "Login failed: email not found — email=%s", email
                )
                raise NotFoundException(
                    detail=f"User with email '{email}' not found",
                )

            if not self._verify_password(password, user.password_hash):
                logger.warning(
                    "Login failed: wrong password — email=%s", email
                )
                raise AppException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect password",
                )

            token = create_access_token(subject=str(user.id))
            logger.info("User logged in: id=%s, email=%s", user.id, email)
            return {"access_token": token, "token_type": "bearer"}

        except (AppException, NotFoundException):
            raise

        except SQLAlchemyError as exc:
            logger.error(
                "DB error during login email=%s: %s", email, exc, exc_info=True
            )
            raise AppException(
                status_code=400,
                detail=f"Database error during login for '{email}'",
            )