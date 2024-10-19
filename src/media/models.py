from sqlalchemy import Column, Integer, String, func, DateTime
from sqlalchemy.orm import relationship, Mapped, mapped_column

from config.database import Base


class Media(Base):
    __tablename__ = "media"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(String(225))
    filename: Mapped[str] = mapped_column(String(225))
    uploaded_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    users = relationship("User", back_populates="media")

    def __str__(self):
        return f"File: {self.filename}"
