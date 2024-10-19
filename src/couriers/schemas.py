from datetime import datetime

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr

from src.media.schemas import MediaSchemas


class CourierUpdate(BaseModel):
    full_name: str
    phone_number: str
    email: EmailStr


class CourierSchemas(BaseModel):
    uuid: UUID
    username: str
    full_name: Optional[str] = None
    phone_number: str


class CourierDetailSchemas(BaseModel):
    uuid: UUID
    username: str
    full_name: Optional[str] = None
    phone_number: str
    email: Optional[EmailStr] = None
    media: Optional[MediaSchemas] = None
    updated_at: Optional[datetime] = None
    registered_at: datetime

    class Config:
        from_attributes = True

# TODO: wallet and work schedule for couriers
