import os
import time
from dotenv import load_dotenv

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from logs.logger import logger

ALLOWED_IMAGE_TYPES = {"image/jpg", "image/jpeg", "image/png", "image/webp"}
UPLOAD_DIR = "static/uploads/"  # директория хранения фотографии

load_dotenv()
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

ESKIZ_EMAIL = os.getenv("ESKIZ_EMAIL")
ESKIZ_PASSWORD = os.getenv("ESKIZ_PASSWORD")

SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = os.getenv('ALGORITHM')

SERVICE_ID = os.getenv('SERVICE_ID')
LOGIN = os.getenv('LOGIN')
PASSWORD = os.getenv('PASSWORD')
STPimsApiPartnerKey = os.getenv('STPimsApiPartnerKey')

REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = os.getenv("REDIS_PORT")
REDIS_DB = os.getenv("REDIS_DB")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")

API_KEY = os.getenv("API_KEY")


# Значение нужно получение в int


# Класс для
class TimeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers['X-Process-Time'] = str(round(time.time()))
        return response


# Если директория static/uploads не существует, то создаем её
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)
    logger.success("Директория: %s успешно создана", UPLOAD_DIR)
