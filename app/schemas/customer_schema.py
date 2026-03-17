# app/schemas/customer_schema.py

from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class CustomerCreate(BaseModel):
    name: str
    phone: Optional[str]
    address: Optional[str]


class CustomerUpdate(BaseModel):
    name: Optional[str]
    phone: Optional[str]
    address: Optional[str]


class CustomerResponse(BaseModel):
    id: str
    user_id: str
    name: str
    phone: Optional[str]
    address: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True