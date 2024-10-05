from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr


class SuperuserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[EmailStr] = None


class SuperuserSchemas(BaseModel):
    uuid: UUID
    username: str
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    registered_at: datetime

    class Config:
        from_attributes = True


class RolesSchemas(BaseModel):
    id: int
    name: str
    description: str
    created_at: datetime

    class Config:
        from_attributes = True
