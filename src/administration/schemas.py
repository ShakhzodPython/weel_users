from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr


class SuperuserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[EmailStr] = None


class SuperuserSchemas(BaseModel):
    id: UUID
    username: str
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[EmailStr] = None
    registered_at: datetime

    class Config:
        from_attributes = True
