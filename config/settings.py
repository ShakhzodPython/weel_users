import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

from logs.logger import logger

env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)


class Settings(BaseSettings):
    DB_USER: str = os.getenv("DB_USER")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD")
    DB_HOST: str = os.getenv("DB_HOST")
    DB_PORT: str = os.getenv("DB_PORT")
    DB_NAME: str = os.getenv("DB_NAME")
    DB_URL: str = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

    # JWT
    JWT_SECRET: str = os.getenv("JWT_SECRET")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_DAYS: int = os.getenv("REFRESH_TOKEN_EXPIRE_DAYS")

    # Redis
    REDIS_HOST: str = os.getenv("REDIS_HOST")
    REDIS_PORT: str = os.getenv("REDIS_PORT")
    REDIS_DB: str = os.getenv("REDIS_DB")
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD")
    REDIS_URL: str = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

    # Eskiz
    ESKIZ_EMAIL: str = os.getenv("ESKIZ_EMAIL")
    ESKIZ_PASSWORD: str = os.getenv("ESKIZ_PASSWORD")

    # U-pay
    SERVICE_ID: str = os.getenv('SERVICE_ID')
    LOGIN: str = os.getenv('LOGIN')
    PASSWORD: str = os.getenv('PASSWORD')
    STPimsApiPartnerKey: str = os.getenv('STPimsApiPartnerKey')

    # others
    API_KEY: str = os.getenv("API_KEY")


ALLOWED_IMAGE_TYPES = {"image/jpg", "image/jpeg", "image/png", "image/webp"}
UPLOAD_DIR = "static/uploads/"

# If the directory static/uploads does not exist, create it
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)
    logger.success("Директория: %s успешно создана", UPLOAD_DIR)


def get_settings() -> Settings:
    return Settings()
