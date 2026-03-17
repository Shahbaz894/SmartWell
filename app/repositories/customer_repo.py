# app/repositories/customer_repo.py

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.models.customer import Customer
from app.core.logger import logger
from app.core.exceptions import AppException, NotFoundException


class CustomerRepository:

    def __init__(self, db: Session):
        self.db = db

    def create_customer(self, customer: Customer):
        try:
            self.db.add(customer)
            self.db.commit()
            self.db.refresh(customer)
            logger.info("Customer created: id=%s, name=%s", customer.id, customer.name)
            return customer
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error("Failed to create customer %s: %s", customer.name, str(e))
            raise AppException(f"Database error: failed to create customer {customer.name}")

    def get_customers(self, user_id: str):
        try:
            customers = self.db.query(Customer).filter(Customer.user_id == user_id).all()
            logger.info("Fetched %d customers for user_id=%s", len(customers), user_id)
            return customers
        except SQLAlchemyError as e:
            logger.error("Failed to fetch customers for user_id=%s: %s", user_id, str(e))
            raise AppException(f"Database error: failed to fetch customers for user_id {user_id}")

    def get_customer_by_id(self, customer_id: str, user_id: str):
        try:
            customer = (
                self.db.query(Customer)
                .filter(Customer.id == customer_id, Customer.user_id == user_id)
                .first()
            )
            if not customer:
                logger.warning("Customer not found: id=%s, user_id=%s", customer_id, user_id)
                raise NotFoundException(f"Customer {customer_id} not found")
            return customer
        except SQLAlchemyError as e:
            logger.error("Failed to fetch customer id=%s: %s", customer_id, str(e))
            raise AppException(f"Database error: failed to fetch customer {customer_id}")

    def delete_customer(self, customer: Customer):
        try:
            self.db.delete(customer)
            self.db.commit()
            logger.info("Customer deleted: id=%s, name=%s", customer.id, customer.name)
            return True
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error("Failed to delete customer %s: %s", customer.id, str(e))
            raise AppException(f"Database error: failed to delete customer {customer.id}")