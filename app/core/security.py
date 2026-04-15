from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.core.exceptions import UnauthorizedAccess
from app.core.logger import logger
from app.services.jwt_handler import JWTHandler


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Validate JWT token and return authenticated user.
    """

    logger.info("Authenticating user via JWT")

    try:
        payload = JWTHandler.verify_token(token)

        user_id = payload.get("sub")

        if not user_id:
            logger.warning("JWT missing 'sub'")
            raise UnauthorizedAccess()

        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            logger.warning("User not found: id=%s", user_id)
            raise UnauthorizedAccess()

        logger.info("User authenticated: %s", user.email)

        return user

    except UnauthorizedAccess:
        raise

    except Exception as e:
        logger.error("Auth error: %s", str(e), exc_info=True)
        raise UnauthorizedAccess()