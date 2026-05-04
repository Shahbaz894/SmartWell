# app/repositories/user_repo.py

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.models.user import User
from app.core.logger import logger
from app.core.exceptions import AppException, NotFoundException


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_user(self, user: User):
        try:
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            logger.info("User created: id=%s, email=%s", user.id, user.email)
            return user

        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error("Failed to create user %s: %s", user.email, str(e), exc_info=True)
            raise AppException(
                status_code=500,
                detail=f"Database error: failed to create user {user.email}",
            )

    def get_user_by_email(self, email: str):
        try:
            user = self.db.query(User).filter(User.email == email).first()

            if not user:
                logger.warning("User not found with email: %s", email)
                raise NotFoundException(f"User with email {email} not found")

            logger.info("Fetched user by email: %s", email)
            return user

        except NotFoundException:
            raise

        except SQLAlchemyError as e:
            logger.error("Failed to fetch user by email %s: %s", email, str(e), exc_info=True)
            raise AppException(
                status_code=500,
                detail=f"Database error: failed to fetch user by email {email}",
            )

    def get_user_by_id(self, user_id: str):
        try:
            user = self.db.query(User).filter(User.id == user_id).first()

            if not user:
                logger.warning("User not found with id: %s", user_id)
                raise NotFoundException(f"User with id {user_id} not found")

            logger.info("Fetched user by id: %s", user_id)
            return user

        except NotFoundException:
            raise

        except SQLAlchemyError as e:
            logger.error("Failed to fetch user by id %s: %s", user_id, str(e), exc_info=True)
            raise AppException(
                status_code=500,
                detail=f"Database error: failed to fetch user by id {user_id}",
            )

    def get_all_users(self):
        try:
            users = self.db.query(User).order_by(User.created_at.desc()).all()
            logger.info("Fetched all users: count=%s", len(users))
            return users

        except SQLAlchemyError as e:
            logger.error("Failed to fetch users: %s", str(e), exc_info=True)
            raise AppException(
                status_code=500,
                detail="Database error: failed to fetch users",
            )

    def delete_user(self, user_id: str):
        try:
            user = self.get_user_by_id(user_id)

            self.db.delete(user)
            self.db.commit()

            logger.info("Deleted user: id=%s", user_id)
            return True

        except NotFoundException:
            raise

        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error("Failed to delete user %s: %s", user_id, str(e), exc_info=True)
            raise AppException(
                status_code=500,
                detail="Database error: failed to delete user",
            )