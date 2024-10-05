import jwt
from fastapi import APIRouter, HTTPException, Depends, Request, status

from slowapi.errors import RateLimitExceeded

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from database.config import ESKIZ_EMAIL, ESKIZ_PASSWORD, SECRET_KEY, ALGORITHM
from database.security import create_access_token, create_refresh_token, get_api_key
from database.settings import get_db
from logs.logger import logger
from src.users.models import User, Role
from .redis import get_verification_code, save_verification_code, increment_attempt, reset_attempts, block_user, \
    get_phone_number
from .sms import send_sms, get_eskiz_token, generate_verification_code
from .utils import check_phone

router_auth = APIRouter(
    tags=["Authorization"],
)


@router_auth.post("/api/v1/auth/sign_up/", status_code=status.HTTP_200_OK)
async def sign_up(request: Request,
                  phone_number: str,
                  db: AsyncSession = Depends(get_db)):
    logger.info("Попытка регистрации с телефон номером: %s", phone_number)
    try:
        valid_phone_number = await check_phone(phone_number)

        existing_phone_number = await db.scalar(
            select(User)
            .where(User.phone_number == phone_number)
        )

        if existing_phone_number:
            logger.error("Пользователь с телефон номер: %s уже существует", phone_number)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="User with this phone number already exist")

        if valid_phone_number:
            verification_code = generate_verification_code()
            await save_verification_code(phone_number, verification_code)

            token = await get_eskiz_token(ESKIZ_EMAIL, ESKIZ_PASSWORD)
            response = await send_sms(request, phone_number,
                                      f"Код верификации для входа в приложение WEEL: {verification_code}",
                                      token)
            if response.get("error"):
                logger.error("Ошибка при отправке SMS на телефон номер: %s", phone_number)
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                    detail=f"Ошибка при отправке SMS на номер: {phone_number}")

            logger.success("СМС код успешно отправлен на телефон номер: %s", phone_number)
            return {"detail": f"СМС код успешно отправлен на телефон номер: {phone_number}"}
        else:
            logger.error("Не верный формат телефон номера")
            return {"detail": "Не верный формат телефон номера"}
    except RateLimitExceeded:
        logger.error("Слишком много запросов")
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests")


@router_auth.post("/api/v1/auth/sign_up/verify/", status_code=status.HTTP_201_CREATED)
async def verify_code(code: str,
                      db: AsyncSession = Depends(get_db)):
    phone_number = await get_phone_number(code)
    logger.info("Проверка кода верификации для телефон номера: %s", phone_number)

    redis_code = await get_verification_code(phone_number)
    if redis_code is None or redis_code != code:
        attempts = await increment_attempt(phone_number)
        remaining_attempts = 4 - attempts
        if remaining_attempts > 0:
            logger.error("Неверный код, попыток осталось: %s", remaining_attempts)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"Неверный код, у вас осталось {remaining_attempts} {'попытка' if remaining_attempts == 1 else 'попытки'}")
        else:
            await block_user(phone_number)
            logger.error("Пользователь заблокирован из-за многократных неудачных попыток")
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                                detail="Вы были временно заблокированы. Пожалуйста, попробуйте еще раз позже.")
    else:
        # Сброс попыток после успешной верификации
        await reset_attempts(phone_number)

    role = await db.scalar(select(Role).where(Role.name == "USER"))

    if role is None:
        logger.error("Роль: USER не найдена")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    # Создание пользователя
    user = User(phone_number=phone_number, roles=[role])
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # генерация JWT токена
    logger.success("Пользователь c телефон номером: %s успешно зарегистрирован c ролью %s", phone_number, role.name)
    access_token = create_access_token(data={"user_uuid": user.uuid, "role": role.name})
    refresh_token = create_refresh_token(
        data={"user_uuid": user.uuid, "role": role.name})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "detail": f"Пользователь: {phone_number} успешно зарегистрирован c ролью {role.name}.",
    }


@router_auth.post("/api/v1/users/token/refresh/", status_code=status.HTTP_201_CREATED)
async def refresh_token(refresh_token: str,
                        db: AsyncSession = Depends(get_db)):
    logger.info("Попытка создания refresh token")
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_uuid = payload.get("user_uuid")
        user_role = payload.get("role")
        if user_role != "USER":
            logger.error("Не корректная роль")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incorrect role")
    except jwt.ExpiredSignatureError:
        logger.error("Refresh token истек")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Refresh token expired")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token invalid")

    role = await db.scalar(select(Role).where(Role.name == "USER"))

    new_access_token = create_access_token(data={"user_uuid": user_uuid, "role": role.name})

    logger.success("Токен успешно обновлён для пользователя с UUID: %s", user_uuid)
    return {
        "access_token": new_access_token
    }
