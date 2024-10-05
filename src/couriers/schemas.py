from datetime import datetime

from typing import Optional
from uuid import UUID

from fastapi import Form, File, UploadFile
from pydantic import BaseModel, EmailStr

from src.media.schemas import MediaSchemas


class CourierUpdate(BaseModel):
    full_name: str
    email: EmailStr
    phone_number: str


class CourierSchemas(BaseModel):
    uuid: UUID
    username: str
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    media: MediaSchemas
    registered_at: datetime

    class Config:
        from_attributes = True
