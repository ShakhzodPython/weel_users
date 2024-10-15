import redis.asyncio as aioredis

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from config.settings import DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME, REDIS_HOST, REDIS_PORT, REDIS_DB

DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

Base = declarative_base()
engine = create_async_engine(DATABASE_URL, echo=True)

AsyncSessionLocal = sessionmaker(expire_on_commit=False, autoflush=False, bind=engine, class_=AsyncSession)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


async def get_redis_connection():
    redis_url = f"redis://{REDIS_HOST}:{REDIS_PORT}"
    return await aioredis.from_url(url=redis_url,
                                   encoding="utf-8",
                                   decode_responses=True,
                                   # password=REDIS_PASSWORD,
                                   db=int(REDIS_DB))


async def close_redis_connection():
    redis = None
    if redis:
        redis = await get_redis_connection()
        redis.close()
