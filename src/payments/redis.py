from uuid import UUID

from database.settings import get_redis_connection
from logs.logger import logger


async def save_confirm_id(user_id: UUID, confirm_id: int):
    redis = None
    try:
        redis = await get_redis_connection()
        await redis.set(f"confirm_id:{user_id}", confirm_id)
    except Exception as e:
        logger.error(f"Ошибка при сохранении confirmed_id в Redis: {e}")
        print(f"Error when saving confirm_id in Redis: {e}")

    finally:
        if redis:
            redis.close()
            logger.info('Redis успешно закрыт')
            await redis.wait_closed()


async def get_confirm_id(user_id: UUID):
    redis = None
    try:
        redis = await get_redis_connection()
        # Получаем confirm_id по ключу, который включает user_id
        confirm_id = await redis.get(f"confirm_id:{user_id}")
        return confirm_id
    except Exception as e:
        logger.error(f"Ошибка при получении confirmed_id из Redis: {e}")
        print(f"Error when retrieving confirm_id from Redis: {e}")
    finally:
        if redis:
            redis.close()
            logger.info('Redis успешно закрыт')
            await redis.wait_closed()


async def save_card(user_id: UUID, card_number: str, expiry_date: str):
    redis = None
    try:
        redis = await get_redis_connection()
        await redis.set(f"card_number:{user_id}", card_number, expire=60)
        await redis.set(f"expiry_date:{user_id}", expiry_date, expire=60)
    except Exception as e:
        logger.error(f"Ошибка при сохранении данных карты в Redis: {e}")
        print(f"Error when saving card data in Redis: {e}")
    finally:
        if redis:
            redis.close()
            logger.info('Redis успешно закрыт')
            await redis.wait_closed()


async def get_card(user_id: UUID):
    redis = None
    try:
        redis = await get_redis_connection()
        card_number = await redis.get(f"card_number:{user_id}")
        expiry_date = await redis.get(f"expiry_date:{user_id}")
        return card_number, expiry_date
    except Exception as e:
        logger.error(f'Ошибка при извлечении данных карты в Redis: {e}')
        print(f"Error when retrieving card data in Redis: {e}")
        return None, None
    finally:
        if redis:
            redis.close()
            logger.info('Redis успешно закрыт')
            await redis.wait_closed()


async def save_uzcard_id(user_id: UUID, uzcard_id: int):
    redis = None
    try:
        redis = await get_redis_connection()
        uzcard_id = await redis.set(f"uzcard_id:{user_id}", uzcard_id)
        return uzcard_id
    except Exception as e:
        logger.error(f"Ошибка при сохранении данных карты в Redis: {e}")
        print(f"Error when saving card data in Redis: {e}")
    finally:
        if redis:
            redis.close()
            logger.info('Redis успешно закрыт')
            await redis.wait_closed()


async def get_uzcard_id(user_id: UUID):
    redis = None
    try:
        redis = await get_redis_connection()
        # Получаем uzcard_id по ключу, который включает user_id
        confirm_id = await redis.get(f"uzcard_id:{user_id}")
        return confirm_id
    except Exception as e:
        logger.error(f"Ошибка при получении confirmed_id из Redis: {e}")
        print(f"Error when retrieving confirm_id from Redis: {e}")
    finally:
        if redis:
            redis.close()
            logger.info('Redis успешно закрыт')
            await redis.wait_closed()


async def save_card_phone(user_id: UUID, card_phone: str):
    redis = None
    try:
        redis = await get_redis_connection()
        card_phone = await redis.set(f"card_phone:{user_id}", card_phone)
        return card_phone
    except Exception as e:
        logger.error(f"Ошибка при сохранении данных карты в Redis: {e}")
        print(f"Error when saving card data in Redis: {e}")
    finally:
        if redis:
            redis.close()
            logger.info('Redis успешно закрыт')
            await redis.wait_closed()


async def get_card_phone(user_id: UUID):
    redis = None
    try:
        redis = await get_redis_connection()
        # Получаем card_phone по ключу, который включает user_id
        card_phone = await redis.get(f"card_phone:{user_id}")
        return card_phone
    except Exception as e:
        logger.error(f"Ошибка при получении confirmed_id из Redis: {e}")
        print(f"Error when retrieving confirm_id from Redis: {e}")
    finally:
        if redis:
            redis.close()
            logger.info('Redis успешно закрыт')
            await redis.wait_closed()


async def save_transaction_id(user_id: UUID, transaction_id: int):
    redis = None
    try:
        redis = await get_redis_connection()
        transaction = await redis.set(f"transaction:{user_id}", transaction_id)
        return transaction
    except Exception as e:
        logger.error(f"Ошибка при сохранении данных карты в Redis: {e}")
        print(f"Error when saving card data in Redis: {e}")
    finally:
        if redis:
            redis.close()
            logger.info('Redis успешно закрыт')
            await redis.wait_closed()


async def get_transaction_id(user_id: UUID):
    redis = None
    try:
        redis = await get_redis_connection()
        # Получаем transition_id по ключу, который включает user_id
        transaction = await redis.get(f"transaction:{user_id}")
        return transaction
    except Exception as e:
        logger.error(f"Ошибка при извлечении транзакции из Redis: {e}")
        print(f"Error when retrieving transaction from Redis: {e}")
    finally:
        if redis:
            redis.close()
            logger.info('Redis успешно закрыт')
            await redis.wait_closed()


async def save_balance(user_id: UUID, balance_id: int):
    redis = None
    try:
        redis = await get_redis_connection()
        balance = await redis.set(f"balance:{user_id}", balance_id)
        return balance
    except Exception as e:
        logger.error(f"Ошибка при сохранении баланса в Redis: {e}")
        print(f"Error when saving balance in Redis: {e}")
    finally:
        if redis:
            redis.close()
            logger.info('Redis успешно закрыт')
            await redis.wait_closed()


async def get_balance(user_id: UUID):
    redis = None
    try:
        redis = await get_redis_connection()
        balance = await redis.get(f"balance:{user_id}")
        return balance
    except Exception as e:
        logger.error(f"Ошибка при получении баланса из Redis: {e}")
        print(f"Error when retrieving balance from Redis: {e}")
    finally:
        if redis:
            redis.close()
            logger.info('Redis успешно закрыт')
            await redis.wait_closed()
