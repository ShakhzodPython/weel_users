from datetime import datetime

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr


class RestaurantEditorUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None


class RestaurantEditorSchemas(BaseModel):
    uuid: UUID
    username: str
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    registered_at: datetime

    class Config:
        from_attributes = True  # Использование from_attributes для автоматического маппинга данных из моделей
