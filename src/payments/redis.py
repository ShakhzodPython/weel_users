from uuid import UUID

from config.database import get_redis_connection, close_redis_connection
from logs.logger import logger


async def save_confirm_id(user_uuid: UUID, confirm_id: int):
    try:
        redis = await get_redis_connection()
        await redis.set(f"confirm_id:{user_uuid}", confirm_id)
    except Exception as e:
        logger.error(f"Ошибка при сохранении confirmed_id в Redis: {e}")
        print(f"Error when saving confirm_id in Redis: {e}")

    finally:
        await close_redis_connection()


async def get_confirm_id(user_uuid: UUID):
    try:
        redis = await get_redis_connection()
        # Получаем confirm_id по ключу, который включает user_uuid
        confirm_id = await redis.get(f"confirm_id:{user_uuid}")
        return confirm_id
    except Exception as e:
        logger.error(f"Ошибка при получении confirmed_id из Redis: {e}")
        print(f"Error when retrieving confirm_id from Redis: {e}")
    finally:
        await close_redis_connection()


async def save_card(user_uuid: UUID, card_number: str, expiry_date: str):
    try:
        redis = await get_redis_connection()
        await redis.set(f"card_number:{user_uuid}", card_number, expire=60)
        await redis.set(f"expiry_date:{user_uuid}", expiry_date, expire=60)
    except Exception as e:
        logger.error(f"Ошибка при сохранении данных карты в Redis: {e}")
        print(f"Error when saving card data in Redis: {e}")
    finally:
        await close_redis_connection()


async def get_card(user_uuid: UUID):
    try:
        redis = await get_redis_connection()
        card_number = await redis.get(f"card_number:{user_uuid}")
        expiry_date = await redis.get(f"expiry_date:{user_uuid}")
        return card_number, expiry_date
    except Exception as e:
        logger.error(f'Ошибка при извлечении данных карты в Redis: {e}')
        print(f"Error when retrieving card data in Redis: {e}")
        return None, None
    finally:
        await close_redis_connection()


async def save_uzcard_id(user_uuid: UUID, uzcard_id: int):
    try:
        redis = await get_redis_connection()
        uzcard_id = await redis.set(f"uzcard_id:{user_uuid}", uzcard_id)
        return uzcard_id
    except Exception as e:
        logger.error(f"Ошибка при сохранении данных карты в Redis: {e}")
        print(f"Error when saving card data in Redis: {e}")
    finally:
        await close_redis_connection()


async def get_uzcard_id(user_uuid: UUID):
    redis = None
    try:
        redis = await get_redis_connection()
        # Получаем uzcard_id по ключу, который включает user_uuid
        confirm_id = await redis.get(f"uzcard_id:{user_uuid}")
        return confirm_id
    except Exception as e:
        logger.error(f"Ошибка при получении confirmed_id из Redis: {e}")
        print(f"Error when retrieving confirm_id from Redis: {e}")
    finally:
        await close_redis_connection()


async def save_card_phone(user_uuid: UUID, card_phone: str):
    try:
        redis = await get_redis_connection()
        card_phone = await redis.set(f"card_phone:{user_uuid}", card_phone)
        return card_phone
    except Exception as e:
        logger.error(f"Ошибка при сохранении данных карты в Redis: {e}")
        print(f"Error when saving card data in Redis: {e}")
    finally:
        await close_redis_connection()


async def get_card_phone(user_uuid: UUID):
    try:
        redis = await get_redis_connection()
        # Получаем card_phone по ключу, который включает user_uuid
        card_phone = await redis.get(f"card_phone:{user_uuid}")
        return card_phone
    except Exception as e:
        logger.error(f"Ошибка при получении confirmed_id из Redis: {e}")
        print(f"Error when retrieving confirm_id from Redis: {e}")
    finally:
        await close_redis_connection()


async def save_transaction_id(user_uuid: UUID, transaction_id: int):
    try:
        redis = await get_redis_connection()
        transaction = await redis.set(f"transaction:{user_uuid}", transaction_id)
        return transaction
    except Exception as e:
        logger.error(f"Ошибка при сохранении данных карты в Redis: {e}")
        print(f"Error when saving card data in Redis: {e}")
    finally:
        await close_redis_connection()


async def get_transaction_id(user_uuid: UUID):
    try:
        redis = await get_redis_connection()
        # Получаем transition_id по ключу, который включает user_uuid
        transaction = await redis.get(f"transaction:{user_uuid}")
        return transaction
    except Exception as e:
        logger.error(f"Ошибка при извлечении транзакции из Redis: {e}")
        print(f"Error when retrieving transaction from Redis: {e}")
    finally:
        await close_redis_connection()


async def save_balance(user_uuid: UUID, balance_id: int):
    try:
        redis = await get_redis_connection()
        balance = await redis.set(f"balance:{user_uuid}", balance_id)
        return balance
    except Exception as e:
        logger.error(f"Ошибка при сохранении баланса в Redis: {e}")
        print(f"Error when saving balance in Redis: {e}")
    finally:
        await close_redis_connection()


async def get_balance(user_uuid: UUID):
    try:
        redis = await get_redis_connection()
        balance = await redis.get(f"balance:{user_uuid}")
        return balance
    except Exception as e:
        logger.error(f"Ошибка при получении баланса из Redis: {e}")
        print(f"Error when retrieving balance from Redis: {e}")
    finally:
        await close_redis_connection()
