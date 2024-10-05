from sqlalchemy import Column, Integer, String, func, DateTime
from sqlalchemy.orm import relationship

from database.settings import Base


class Media(Base):
    __tablename__ = "media"
    id = Column(Integer, primary_key=True)
    url = Column(String(225), nullable=False)
    filename = Column(String(225), nullable=False)
    uploaded_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="media")

    def __str__(self):
        return f"File: {self.filename}"
