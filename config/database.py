import redis.asyncio as redis

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from config.settings import get_settings

ASYNC_SQLALCHEMY_DATABASE_URL = get_settings().DB_URL
REDIS_URL = get_settings().REDIS_URL

engine = create_async_engine(
    ASYNC_SQLALCHEMY_DATABASE_URL,
    echo=True
)

AsyncSessionLocal = sessionmaker(expire_on_commit=False, autoflush=False, bind=engine, class_=AsyncSession)

Base = declarative_base()


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


async def get_redis_connection():
    return await redis.from_url(url=REDIS_URL,
                                encoding="utf-8",
                                # password=REDIS_PASSWORD,
                                decode_responses=True)


async def close_redis_connection(redis_connection):
    if redis_connection:
        await redis_connection.aclose()
