from datetime import datetime

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr


class RestaurantEditorUpdate(BaseModel):
    username: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None


class RestaurantEditorSchemas(BaseModel):
    id: UUID
    username: str
    phone_number: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    registered_at: datetime

    class Config:
        from_attributes = True  # Использование from_attributes для автоматического маппинга данных из моделей
