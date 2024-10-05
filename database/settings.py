import time
import aioredis  # использовать версию aioredis==1.3.1

from fastapi import Request

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from starlette.middleware.base import BaseHTTPMiddleware

from database.config import DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME, REDIS_HOST, REDIS_PORT, REDIS_DB

ALLOWED_IMAGE_TYPES = {"image/jpg", "image/jpeg", "image/png", "image/webp"}
UPLOAD_DIR = "uploads/"  # директория хранения фотографии

DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

Base = declarative_base()
engine = create_async_engine(DATABASE_URL, echo=True)

# Фабрика асинхронных сессий
AsyncSessionLocal = sessionmaker(expire_on_commit=False, autoflush=False, bind=engine, class_=AsyncSession)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


async def get_redis_connection():
    redis_url = f"redis://{REDIS_HOST}:{REDIS_PORT}"
    # Подключение к Redis
    return await aioredis.create_redis_pool(address=redis_url,
                                            encoding="utf-8",
                                            # password=REDIS_PASSWORD,
                                            db=int(REDIS_DB))


# Класс для
class TimeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers['X-Process-Time'] = str(round(time.time()))
        return response
