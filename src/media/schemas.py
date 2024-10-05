from datetime import datetime

from pydantic import BaseModel


class MediaSchemas(BaseModel):
    id: int
    url: str
    filename: str
    uploaded_at: datetime

    class Config:
        from_attributes = True
