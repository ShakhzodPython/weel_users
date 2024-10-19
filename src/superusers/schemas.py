from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr


class SuperuserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[EmailStr] = None


class SuperuserSchemas(BaseModel):
    username: str
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    updated_at: Optional[datetime] = None
    registered_at: datetime

    class Config:
        from_attributes = True


class RolesSchemas(BaseModel):
    id: int
    name: str
    description: str
    updated_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
