from sqlalchemy.orm import Session

from app.repositories.user_repo import UserRepository


class UserService:
    def __init__(self, db: Session):
        self.repo = UserRepository(db)

    def get_all_users(self):
        return self.repo.get_all_users()

    def get_user_by_id(self, user_id: str):
        return self.repo.get_user_by_id(user_id)

    def delete_user(self, user_id: str):
        return self.repo.delete_user(user_id)