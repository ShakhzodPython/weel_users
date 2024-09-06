import os

from dotenv import load_dotenv

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
SUCCESS_LEVEL_NUM = int(os.getenv("SUCCESS_LEVEL_NUM"))
