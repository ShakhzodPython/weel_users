import bcrypt
import uuid

from sqlalchemy import Integer, String, DateTime, ForeignKey, Table, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from config.database import Base
from src.media.models import Media


class Role(Base):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[DateTime | None] = mapped_column(DateTime, onupdate=func.now(), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    users = relationship("User", back_populates="roles")


class User(Base):
    __tablename__ = "user"
    uuid: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=True)
    hash_password: Mapped[str] = mapped_column(String(128), nullable=True)
    phone_number: Mapped[str] = mapped_column(String(11), unique=True)
    full_name: Mapped[str] = mapped_column(String(100), nullable=True)
    email: Mapped[str] = mapped_column(String(100), nullable=True, unique=True)
    image_id: Mapped[int] = mapped_column(Integer, ForeignKey("media.id"), nullable=True)
    role_id: Mapped[int] = mapped_column(Integer, ForeignKey("roles.id"))
    updated_at: Mapped[DateTime | None] = mapped_column(DateTime, onupdate=func.now(), nullable=True)
    registered_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    roles = relationship("Role", back_populates="users")
    cards = relationship("Card", back_populates="users", cascade="all, delete")
    media = relationship(Media, back_populates="users")
    wallet = relationship("Wallet", back_populates="users")
    work_schedule = relationship("WorkSchedule", back_populates="users")

    def set_password(self, password: str):
        self.hash_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode('utf-8')

    def verify_password(self, password: str) -> bool:
        return bcrypt.checkpw(password.encode(), self.hash_password.encode())

    def __str__(self):
        return self.phone_number


class Card(Base):
    __tablename__ = "cards"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_uuid: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('user.uuid'))
    card_number_hashed: Mapped[str] = mapped_column(String(225), unique=True)
    expiry_date_hashed: Mapped[str] = mapped_column(String(225))
    is_blacklisted: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[DateTime | None] = mapped_column(DateTime, onupdate=func.now(), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    users = relationship("User", back_populates="cards")

    def __str__(self):
        return


class Wallet(Base):
    __tablename__ = "wallet"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_uuid: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('user.uuid'))
    card_id: Mapped[int] = mapped_column(Integer, ForeignKey("cards.id"))
    profit: Mapped[int] = mapped_column(Integer)  # заплата
    updated_at: Mapped[DateTime | None] = mapped_column(DateTime, onupdate=func.now(), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    users = relationship("User", back_populates="wallet")

    def __repr__(self):
        return f"User: {self.user.username} | {self.profit}"


class WorkSchedule(Base):
    __tablename__ = "work_schedule"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_uuid: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('user.uuid'))
    day_of_week: Mapped[str] = mapped_column(String, nullable=False)
    start_time: Mapped[int] = mapped_column(Integer, nullable=False)
    end_time: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[DateTime | None] = mapped_column(DateTime, onupdate=func.now(), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"User: {self.user.username} | {self.day_of_week}"

    users = relationship("User", back_populates="work_schedule")