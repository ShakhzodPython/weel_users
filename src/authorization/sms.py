import requests

from fastapi import Request, HTTPException, status

from random import randint
from aiohttp import ClientSession

from logs.logger import logger
from src.authorization.rate_limeter import limiter
from src.authorization.redis import get_redis_connection


def generate_verification_code():
    code = randint(1000, 9999)
    logger.success(f"Код для подтверждения сгенерирован успешно: {code}")
    return code


async def get_eskiz_token(email: str, password: str):
    redis = await get_redis_connection()
    token = await redis.get("eskiz_token")
    if token:
        logger.info("Найдите токен Eskiz в Redis")
        return token

    url = "https://notify.eskiz.uz/api/auth/login"
    payload = {
        "email": email,
        "password": password
    }
    try:
        response = requests.post(url, data=payload)
        response_data = response.json()
        if response.status_code == 200 and "data" in response_data:
            token = response_data["data"]["token"]
            await redis.set("eskiz_token", token, expire=3600)
            logger.info("Новый токен Eskiz извлекается и хранится в Redis")
        else:
            logger.error("Не удалось пройти аутентификацию в API Eskiz")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Не удалось пройти аутентификацию в API Eskiz")
    finally:
        redis.close()
        await redis.wait_closed()
    return token


@limiter.limit("2/minute")
async def send_sms(request: Request, phone_number: str, message: str, token: str):
    url = "https://notify.eskiz.uz/api/message/sms/send"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "mobile_phone": phone_number,
        "message": message,
        "from": "4546"
    }

    async with ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as response:
            response_data = await response.json()
            if response.status == 200:
                logger.info(f"SMS успешно был отправлен на {phone_number}")
                return response_data

            else:
                error_details = response_data.get("detail", "Failed to send SMS")
                logger.error(f"Ошибка при отправке смс: {error_details}")
                return {
                    "error": True,
                    "details": error_details
                }
