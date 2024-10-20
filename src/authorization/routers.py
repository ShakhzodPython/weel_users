import jwt

from fastapi import APIRouter, HTTPException, Depends, Request, status, Form

from slowapi.errors import RateLimitExceeded

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from config.settings import get_settings
from config.security import create_access_token, create_refresh_token
from config.database import get_db
from logs.logger import logger
from src.users.models import User, Role
from .redis import get_verification_code, save_verification_code, increment_attempt, reset_attempts, block_user, \
    get_phone_number
from .sms import send_sms, get_eskiz_token, generate_verification_code
from .utils import check_phone

router_auth = APIRouter(
    prefix="/auth",
    tags=["authorization"],
)

settings = get_settings()


# TODO: integrate celery with sending sms
@router_auth.post("/sign_up", status_code=status.HTTP_200_OK)
async def sign_up(request: Request,
                  phone_number: str = Form(...),
                  db: AsyncSession = Depends(get_db)):
    logger.info("Попытка регистрации с телефон номером: %s", phone_number)
    try:
        valid_phone_number = await check_phone(phone_number)

        existing_user = await db.scalar(
            select(User)
            .where(User.phone_number == valid_phone_number)
        )

        if existing_user:
            logger.error("Пользователь с телефон номер: %s уже существует", valid_phone_number)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="User with this phone number already exist")

        verification_code = generate_verification_code()
        await save_verification_code(valid_phone_number, verification_code)

        token = await get_eskiz_token(settings.ESKIZ_EMAIL, settings.ESKIZ_PASSWORD)
        response = await send_sms(request, valid_phone_number,
                                  f"Код верификации для входа в приложение WEEL: {verification_code}",
                                  token)
        if response.get("error"):
            logger.error("Ошибка при отправке SMS на телефон номер: %s", valid_phone_number)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"Ошибка при отправке SMS на номер: {valid_phone_number}")

        logger.success("СМС код успешно отправлен на телефон номер: %s", valid_phone_number)
        return {"detail": f"СМС код успешно отправлен на телефон номер: {valid_phone_number}"}
    except RateLimitExceeded:
        logger.error("Слишком много запросов")
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests")


@router_auth.post("/sign_up/verify", status_code=status.HTTP_201_CREATED)
async def verify_code(code: str = Form(...),
                      db: AsyncSession = Depends(get_db)):
    phone_number = await get_phone_number(code)

    if not phone_number:
        logger.error("Код верификации недействителен или истёк")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Код верификации истёк")

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

    role = await db.scalar(select(Role).where(Role.title == "user"))
    if role is None:
        logger.error("Роль: user не найдена")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    # Создание пользователя
    user = User(phone_number=phone_number, role_id=role.id)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # генерация JWT токена
    logger.success("Пользователь c телефон номером: %s успешно зарегистрирован c ролью %s", phone_number, role.title)
    access_token = create_access_token(data={"user_uuid": str(user.uuid), "role": role.title})
    refresh_token = create_refresh_token(data={"user_uuid": str(user.uuid), "role": role.title})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "detail": f"Пользователь: {phone_number} успешно зарегистрирован",
    }


@router_auth.post("/users/token/refresh", status_code=status.HTTP_201_CREATED)
async def refresh_token(refresh_token: str = Form(...),
                        db: AsyncSession = Depends(get_db)):
    logger.info("Попытка создания refresh token")
    try:
        payload = jwt.decode(refresh_token, settings.JWT_SECRET, algorithms=settings.JWT_ALGORITHM)
        user_uuid = payload.get("user_uuid")
        role = payload.get("role")
        if role != "user":
            logger.error("Не корректная роль")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incorrect role")
    except jwt.ExpiredSignatureError:
        logger.error("Refresh token истек")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Refresh token expired")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token invalid")

    role = await db.scalar(select(Role).where(Role.title == "user"))
    access_token = create_access_token(data={"user_uuid": user_uuid, "role": role.title})

    logger.success("Токен успешно обновлён для пользователя с UUID: %s", user_uuid)
    return {
        "access_token": access_token
    }
