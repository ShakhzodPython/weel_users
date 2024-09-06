from typing import List
from uuid import UUID

import jwt
from fastapi import APIRouter, Form, Depends, HTTPException, Response, status
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.config import SECRET_KEY, ALGORITHM
from database.security import create_access_token, create_refresh_token, is_courier, get_api_key, is_superuser
from database.settings import get_db
from logs.logger import logger
from src.administration.utils import validate_password, validate_username
from src.couriers.schemas import CourierSchemas, CourierUpdate
from src.users.models import User, Role

router_couriers = APIRouter(
    tags=["Couriers"]
)


@router_couriers.post("/api/v1/auth/couriers/sign_up/", status_code=status.HTTP_201_CREATED)
async def sign_up(username: str = Form(...),
                  password: str = Form(...),
                  api_key: str = Depends(get_api_key),
                  db: AsyncSession = Depends(get_db)):
    logger.info(f"Попытка создания курьера с именем пользователя: {username}")

    stmt = await db.execute(select(Role).where(Role.name == "COURIER"))
    role = stmt.scalars().one_or_none()

    if not role:
        logger.error(f"Роль: COURIER не найдена")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    existing_username_stmt = await db.execute(select(User).where(User.username == username))
    existing_username = existing_username_stmt.scalars().one_or_none()
    if existing_username:
        logger.error(f"Курьер с именем пользователя: {username} уже существует")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Username already exist")

    new_courier = User(username=validate_username(username), roles=[role])
    new_courier.set_password(validate_password(password))
    db.add(new_courier)
    await db.commit()
    await db.refresh(new_courier)

    logger.success(f"Курьер с именем пользователем: {username} создался успешно")
    return {"detail": f"Courier: {username} created successfully"}


@router_couriers.post("/api/v1/auth/couriers/sign_in/", status_code=status.HTTP_200_OK)
async def sign_in(username: str = Form(...),
                  api_key: str = Depends(get_api_key),
                  password: str = Form(...),
                  db: AsyncSession = Depends(get_db)):
    logger.info(f"Попытка входа в аккаунт с именем пользователя: {username}")

    stmt = await db.execute(select(User).options(selectinload(User.roles)).where(
        User.roles.any(name="COURIER"), User.username == username))
    courier = stmt.scalars().one_or_none()

    if courier is None or not courier.verify_password(password):
        logger.error(f"Не верное имя пользователя или пароль")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect username or password")

    access_token = create_access_token(
        data={"user_id": courier.id, "role": courier.roles[0].name})
    refresh_token = create_refresh_token(
        data={"user_id": courier.id, "role": courier.roles[0].name})

    logger.success(f"Курьер с именем пользователя: {username} вошел в аккаунт успешно")
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "detail": f"Courier: {username} logged into the account successfully"
    }


@router_couriers.post("/api/v1/couriers/token/refresh/", status_code=status.HTTP_201_CREATED)
async def refresh_token(refresh_token: str,
                        api_key: str = Depends(get_api_key),
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
                         courier_update: CourierUpdate,
                         current_user: User = Depends(is_courier),
                         db: AsyncSession = Depends(get_db)):
    logger.info(f"Попытка обновления курьера с UUID: {courier_id}")

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
        select(User).where(User.email == courier_update.email, User.id != courier_id))
    existing_email = existing_email_stmt.scalars().one_or_none()

    existing_phone_number_stmt = await db.execute(
        select(User).where(User.phone_number == courier_update.phone_number, User.id != courier_id))
    existing_phone_number = existing_phone_number_stmt.scalars().one_or_none()

    if existing_email:
        logger.error(f"Пользователь с email: {courier_update.email} уже существует")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Courier with this email already exist")
    elif existing_phone_number:
        logger.error(f"Курьер с номером телефона: {courier_update.phone_number} уже существует")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Courier with this phone number already exist")
    else:
        for var, value in courier_update.dict(exclude_unset=True).items():
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
