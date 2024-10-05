from datetime import datetime

from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, EmailStr


class CardSchemas(BaseModel):
    id: int
    is_blacklisted: bool

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    phone_number: Optional[str] = None


class UserSchemas(BaseModel):
    uuid: UUID
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: str
    cards: List[CardSchemas]
    registered_at: datetime

    class Config:
        from_attributes = True  # Использование from_attributes для автоматического маппинга данных из моделей
