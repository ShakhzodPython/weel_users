import uuid

from database.settings import get_redis_connection
from logs.logger import logger


async def save_verification_code(phone_number: str, code: str):
    redis = None
    try:
        redis = await get_redis_connection()
        await redis.set(f"verification_code:{code}", phone_number, expire=180)
        await redis.set(f"phone_number:{phone_number}", code, expire=180)
        logger.success(f"Код подтверждения успешно сохранен для {phone_number}")
    except Exception as e:
        logger.error(f"Произошла ошибка при сохранений кода подтверждения: {e}")
    finally:
        if redis:
            redis.close()
            await redis.wait_closed()


async def get_phone_number(code: str):
    redis = None
    try:
        redis = await get_redis_connection()
        phone_number = await redis.get(f"verification_code:{code}")
        if phone_number:
            logger.info(f"Номер телефона, полученный по коду {code}.")
        else:
            logger.error(f"Не найден номер телефона для кода {code}.")
        return phone_number
    finally:
        if redis:
            redis.close()
            await redis.wait_closed()


async def get_verification_code(phone_number: str):
    redis = None
    try:
        redis = await get_redis_connection()
        code = await redis.get(f"phone_number:{phone_number}")
        if code:
            logger.info(f"Код подтверждения получен для {phone_number}.")
        else:
            logger.error(f"Не найден код подтверждения для {phone_number}.")
        return code
    finally:
        if redis:
            redis.close()
            await redis.wait_closed()


async def increment_attempt(phone_number: str):
    redis = None
    try:
        redis = await get_redis_connection()
        attempts_key = f"attempts:{phone_number}"
        attempts = await redis.incr(attempts_key)
        await redis.expire(attempts_key, 300)  # Счетчик сбрасывается через 5 минут
        logger.info(f"Количество попыток для {phone_number}. Текущая попытка: {attempts}.")
        return attempts
    finally:
        if redis:
            redis.close()
            await redis.wait_closed()


async def block_user(phone_number: str):
    redis = None
    try:
        redis = await get_redis_connection()
        block_key = f"block:{phone_number}"
        await redis.set(block_key, "blocked", expire=300)  # Блокировка на 5 минут
        logger.info(f"Пользователь: {phone_number} был заблокирован на 5 минут")
    finally:
        if redis:
            redis.close()
            await redis.wait_closed()


# Проверка заблокирован ли пользователь
async def is_user_blocked(phone_number: str):
    redis = None
    try:
        redis = await get_redis_connection()
        block_key = f"block:{phone_number}"
        blocked = await redis.exists(block_key)
        if blocked:
            logger.info(f"Пользователь: {phone_number} временно заблокирован.")
        else:
            logger.info(f"Пользователь: {phone_number} не заблокирован.")
        return blocked
    finally:
        if redis:
            redis.close()
            await redis.wait_closed()


# Сброс попыток
async def reset_attempts(phone_number: str):
    redis = None
    try:
        redis = await get_redis_connection()
        key = f"{phone_number}_attempts"
        await redis.delete(key)
        logger.info(f"Счетчик попыток для {phone_number} был сброшен")
    finally:
        if redis:
            redis.close()
            await redis.wait_closed()
