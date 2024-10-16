import bcrypt
import uuid

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Table, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from config.database import Base
from src.media.models import Media


class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


class User(Base):
    __tablename__ = "user"
    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    username = Column(String(100), unique=True, nullable=True)
    hash_password = Column(String(128), nullable=True)
    phone_number = Column(String(11), unique=True)
    full_name = Column(String(100), nullable=True)
    email = Column(String(100), nullable=True, unique=True)
    image = Column(Integer, ForeignKey("media.id"), nullable=True)
    updated_at = Column(DateTime, onupdate=func.now(), nullable=True)
    registered_at = Column(DateTime, server_default=func.now())

    roles = relationship("Role", secondary="user_roles")
    cards = relationship("Card", back_populates="user", cascade="all, delete")
    media = relationship(Media, back_populates="user")

    def set_password(self, password: str):
        self.hash_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode('utf-8')

    def verify_password(self, password: str) -> bool:
        return bcrypt.checkpw(password.encode(), self.hash_password.encode())

    def __str__(self):
        return self.phone_number


class Card(Base):
    __tablename__ = "cards"
    id = Column(Integer, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('user.uuid'))
    user = relationship("User", back_populates="cards")
    card_number_hashed = Column(String(225), unique=True)
    expiry_date_hashed = Column(String(225))
    is_blacklisted = Column(Boolean, default=False)
    updated_at = Column(DateTime, onupdate=func.now(), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"User: {self.user.full_name} | {self.user.phone_number}"


class Wallet(Base):
    __tablename__ = "wallet"
    id = Column(Integer, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('user.uuid'))
    card_id = Column(Integer, ForeignKey("cards.id"))
    profit = Column(Integer)
    updated_at = Column(DateTime, onupdate=func.now(), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"User: {self.user.username} | {self.profit}"


class WorkSchedule(Base):
    __tablename__ = "work_schedule"
    id = Column(Integer, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('user.uuid'))
    day_of_week = Column(String, nullable=False)
    start_time = Column(Integer, nullable=False)
    end_time = Column(Integer, nullable=False)
    updated_at = Column(DateTime, onupdate=func.now(), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"User: {self.user.username} | {self.day_of_week}"


user_roles = Table(
    "user_roles",
    Base.metadata,
    Column('user_id', UUID(as_uuid=True), ForeignKey('user.uuid'), primary_key=True),
    Column('role_id', Integer, ForeignKey('roles.id'), primary_key=True)
)
