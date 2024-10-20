from datetime import datetime

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr

from src.media.schemas import MediaSchemas


class RestaurantOwnerUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None


class RestaurantOwnerSchemas(BaseModel):
    uuid: UUID
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    updated_at: Optional[datetime] = None
    registered_at: datetime

    class Config:
        from_attributes = True


class RestaurantOwnerDetailSchemas(BaseModel):
    uuid: UUID
    full_name: Optional[str] = None
    # cards: List[CardSchemas]
    email: Optional[EmailStr] = None
    media: Optional[MediaSchemas] = None
    phone_number: Optional[str] = None
    updated_at: Optional[datetime] = None
    registered_at: datetime

    class Config:
        from_attributes = True
