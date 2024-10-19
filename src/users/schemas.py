from datetime import datetime

from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, EmailStr

from src.superusers.schemas import RolesSchemas


class CardSchemas(BaseModel):
    id: int
    is_blacklisted: bool

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None


class UserSchemas(BaseModel):
    uuid: UUID
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: str
    updated_at: Optional[datetime] = None
    registered_at: datetime

    class Config:
        from_attributes = True


class UserDetailSchemas(BaseModel):
    uuid: UUID
    full_name: Optional[str] = None
    roles: RolesSchemas
    cards: List[CardSchemas]
    email: Optional[EmailStr] = None
    phone_number: str
    updated_at: Optional[datetime] = None
    registered_at: datetime

    class Config:
        from_attributes = True
