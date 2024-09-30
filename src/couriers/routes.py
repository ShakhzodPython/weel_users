import jwt

from typing import List
from uuid import UUID

from fastapi import APIRouter, Request, Form, Depends, HTTPException, Response, status
from slowapi.errors import RateLimitExceeded
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.config import SECRET_KEY, ALGORITHM, ESKIZ_EMAIL, ESKIZ_PASSWORD
from database.security import create_access_token, create_refresh_token, is_courier, get_api_key, is_superuser
from database.settings import get_db
from logs.logger import logger
from src.administration.utils import validate_password
from src.authorization.redis import save_verification_code, get_phone_number, get_verification_code, increment_attempt, \
    block_user, reset_attempts
from src.authorization.sms import generate_verification_code, get_eskiz_token, send_sms
from src.authorization.utils import check_phone
from src.couriers.schemas import CourierSchemas, CourierUpdate
from src.users.models import User, Role

router_couriers = APIRouter(
    tags=["Couriers"]
)


@router_couriers.post("/api/v1/auth/couriers/sign_up/", status_code=status.HTTP_201_CREATED)
async def sign_up(
        request: Request,
        phone_number: str = Form(...),
        db: AsyncSession = Depends(get_db)):
    logger.info(f"Попытка создания курьера с телефон номером: {phone_number}")
    try:
        valid_phone_number = await check_phone(phone_number)

        existing_phone_number_stmt = await db.execute(select(User).options(selectinload(User.roles)).where(
            User.roles.any(name="COURIER"), User.phone_number == phone_number))
        existing_phone_number = existing_phone_number_stmt.scalars().one_or_none()
        if existing_phone_number:
            logger.error(f"Курьер с телефон номером: {phone_number} уже существует")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="Courier with this phone number already exist")

        if valid_phone_number:
            verification_code = generate_verification_code()
            await save_verification_code(phone_number, verification_code)

            token = await get_eskiz_token(ESKIZ_EMAIL, ESKIZ_PASSWORD)
            response = await send_sms(request, phone_number,
                                      f"Код верификации для входа в приложение WEEL: {verification_code}",
                                      token)
            if response.get("error"):
                logger.error(f"Ошибка при отправке SMS на телефон номер: {phone_number}")
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                    detail=f"Ошибка при отправке SMS на номер: {phone_number}")

            logger.success(f"СМС код успешно отправлен на телефон номер курьеру: {phone_number}")
            return {"detail": f"СМС код успешно отправлен на телефон номер курьеру: {phone_number}"}
        else:
            logger.error("Не верный формат телефон номера")
            return {"detail": "Не верный формат телефон номера"}
    except RateLimitExceeded:
        logger.error("Слишком много запросов")
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests")


@router_couriers.post("/api/v1/couriers/sign_up/verify/", status_code=status.HTTP_201_CREATED)
async def verify_code(code: str,
                      password: str,
                      db: AsyncSession = Depends(get_db)):
    # Извлечение номера телефона из Redis по коду
    phone_number = await get_phone_number(code)
    logger.info(f"Проверка кода верификации для телефон номера: {phone_number}")

    redis_code = await get_verification_code(phone_number)
    if redis_code is None or redis_code != code:
        attempts = await increment_attempt(phone_number)
        remaining_attempts = 4 - attempts
        if remaining_attempts > 0:
            logger.error(f"Неверный код, попыток осталось: {remaining_attempts}")
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

        role_stmt = await db.execute(select(Role).where(Role.name == "COURIER"))
        role = role_stmt.scalars().one_or_none()

    if role is None:
        logger.error("Роль: COURIER не найдена")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    # Создание пользователя
    user = User(phone_number=phone_number, roles=[role])
    user.set_password(validate_password(password))

    db.add(user)
    await db.commit()
    await db.refresh(user)

    # генерация JWT токена
    logger.success(f"Пользователь {phone_number} успешно зарегистрирован c ролью {role.name}.")
    return {
        "detail": f"Пользователь: {phone_number} успешно зарегистрирован c ролью {role.name}."
    }


@router_couriers.post("/api/v1/auth/couriers/sign_in/", status_code=status.HTTP_200_OK)
async def sign_in(phone_number: str = Form(...),
                  password: str = Form(...),
                  db: AsyncSession = Depends(get_db)):
    logger.info(f"Попытка входа в аккаунт с телефон номером: {phone_number}")

    stmt = await db.execute(select(User).options(selectinload(User.roles)).where(
        User.roles.any(name="COURIER"), User.phone_number == phone_number))
    courier = stmt.scalars().one_or_none()

    if courier is None or not courier.verify_password(password):
        logger.error(f"Не верный телефон номер или пароль")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect phone number or password")

    access_token = create_access_token(
        data={"user_id": courier.id, "role": courier.roles[0].name})
    refresh_token = create_refresh_token(
        data={"user_id": courier.id, "role": courier.roles[0].name})

    logger.success(f"Курьер с телефон номер: {phone_number} вошел в аккаунт успешно")
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "detail": f"Courier: {phone_number} logged into the account successfully"
    }


@router_couriers.post("/api/v1/couriers/token/refresh/", status_code=status.HTTP_201_CREATED)
async def refresh_token(refresh_token: str,
                        db: AsyncSession = Depends(get_db)):
    logger.info("Попытка создания refresh token")

    try:
        payload = jwt.decode(jwt=refresh_token, key=SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        courier_role = payload.get("role")

        if courier_role != "COURIER":
            logger.error("Роль: COURIER не найдена")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    except jwt.ExpiredSignatureError:
        logger.error("Refresh token истек")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Refresh token expired")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token invalid")

    stmt = await db.execute(select(Role).where(Role.name == "COURIER"))
    role = stmt.scalars().one_or_none()

    new_access_token = create_access_token(data={"user_id": user_id, "role": role.name})
    logger.success(f"Токен успешно обновлён для курьера с UUID: {user_id}")
    return {"access_token": new_access_token}


@router_couriers.get("/api/v1/couriers/", response_model=List[CourierSchemas], status_code=status.HTTP_200_OK)
async def get_couriers(
        current_user: User = Depends(is_superuser),
        api_key: str = Depends(get_api_key),
        db: AsyncSession = Depends(get_db)):
    logger.info("Попытка получения всех курьеров")

    stmt = await db.execute(select(User).options(selectinload(User.roles)).where(User.roles.any(name="COURIER")))
    couriers = stmt.scalars().all()
    logger.success("Все курьеры получены успешно")
    return [CourierSchemas.from_orm(courier) for courier in couriers]


@router_couriers.get("/api/v1/couriers/{courier_id}/", response_model=CourierSchemas, status_code=status.HTTP_200_OK)
async def get_courier_by_id(courier_id: UUID,
                            current_user: User = Depends(is_courier),
                            db: AsyncSession = Depends(get_db)):
    logger.info(f"Попытка получение курьера с UUID: {courier_id}")

    if "SUPERUSER" not in [role.name for role in current_user.roles] and current_user.id != courier_id:
        logger.error("Доступ запрещен: У вас недостаточно прав")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Access denied: You don't have enough privileges")

    stmt = await db.execute(
        select(User).options(selectinload(User.roles)).where(User.id == courier_id, User.roles.any(name="COURIER")))
    courier = stmt.scalars().one_or_none()

    if not courier:
        logger.error(f"Курьер c UUID: {courier_id} не найден")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Courier not found")

    logger.success(f"Курьер с UUID: {courier_id} получен успешно")
    return CourierSchemas.from_orm(courier)


@router_couriers.put("/api/v1/couriers/{courier_id}/", response_model=CourierSchemas, status_code=status.HTTP_200_OK)
async def update_courier(courier_id: UUID,
                         objects: CourierUpdate,
                         current_user: User = Depends(is_courier),
                         db: AsyncSession = Depends(get_db)):
    logger.info(f"Попытка обновить курьера с UUID: {courier_id}")

    if "SUPERUSER" not in [role.name for role in current_user.roles] and courier_id != current_user.id:
        logger.error("Доступ запрещен: У вас недостаточно прав")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Access denied: You don't have enough privileges")

    stmt = await db.execute(select(User).options(selectinload(User.roles)).where(
        User.roles.any(name="COURIER"), User.id == courier_id))
    courier = stmt.scalars().one_or_none()

    if not courier:
        logger.error(f"Курьер c UUID: {courier_id} не найден")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Courier not found")

    existing_email_stmt = await db.execute(
        select(User).where(User.email == objects.email, User.id != courier_id))
    existing_email = existing_email_stmt.scalars().one_or_none()

    existing_phone_number_stmt = await db.execute(
        select(User).where(User.phone_number == objects.phone_number, User.id != courier_id))
    existing_phone_number = existing_phone_number_stmt.scalars().one_or_none()

    if existing_email:
        logger.error(f"Пользователь с email: {objects.email} уже существует")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Courier with this email already exist")
    elif existing_phone_number:
        logger.error(f"Курьер с номером телефона: {objects.phone_number} уже существует")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Courier with this phone number already exist")
    else:
        for var, value in objects.dict(exclude_unset=True).items():
            setattr(courier, var, value)

    db.add(courier)
    await db.commit()
    await db.refresh(courier)
    logger.success(f"Курьер c UUID: {courier_id} успешно обновлен")
    return CourierSchemas.from_orm(courier)


@router_couriers.delete("/api/v1/couriers/{courier_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_courier(courier_id: UUID,
                         current_user: User = Depends(is_courier),
                         db: AsyncSession = Depends(get_db)):
    logger.info(f"Попытка удаления курьера с UUID: {courier_id}")

    if "SUPERUSER" not in [role.name for role in current_user.roles] and courier_id != current_user.id:
        logger.error("Доступ запрещен: У вас недостаточно прав")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Access denied: You don't have enough privileges")

    stmt = await db.execute(select(User).where(User.id == courier_id))
    courier = stmt.scalars().one_or_none()

    if not courier:
        logger.error(f"Курьер c UUID: {courier_id} не найден")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    await db.delete(courier)
    await db.commit()
    logger.success(f"Курьер c UUID: {courier_id} успешно удален")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
