from typing import List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Query, Response, status
from fastapi_filter import FilterDepends
from fastapi_pagination import Page, paginate
from sqlalchemy import asc, exists, not_

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from logs.logger import logger
from src.users.filters import UsersFilter
from src.users.models import User, Card
from src.users.schemas import UserSchemas, UserUpdate, UserDetailSchemas
from config.security import get_current_user, is_superuser
from config.database import get_db

router_users = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router_users.get("/", response_model=Page[UserSchemas],
                  status_code=status.HTTP_200_OK)
async def get_users(
        filters: UsersFilter = FilterDepends(UsersFilter),
        current_user: User = Depends(is_superuser),
        db: AsyncSession = Depends(get_db)):
    logger.info("Попытка получения всех пользователей")

    query = await db.scalars(
        filters.filter(
            select(User)
            .where(User.roles.has(title="USER"))  # has -> использоваться для связей один-к-одному или многие-к-одному
        ))

    users = query.all()

    logger.success("Пользователи успешно получены")
    return paginate(users)


@router_users.get("/{user_uuid}", response_model=UserDetailSchemas, status_code=status.HTTP_200_OK)
async def get_user_by_uuid(user_uuid: UUID,
                           current_user: User = Depends(get_current_user),
                           db: AsyncSession = Depends(get_db)):
    logger.info("Попытка получение пользователя с UUID: %s", user_uuid)

    user = await db.scalar(
        select(User)
        .options(selectinload(User.roles))
        .where(User.roles.has(title="USER"), User.uuid == user_uuid)
    )

    if user is None:
        logger.error("Пользователь c UUID: %s не найден", user_uuid)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if "SUPERUSER" not in [role.name for role in current_user.roles] and user_uuid != current_user.uuid:
        logger.error("Доступ запрещен: У вас недостаточно прав")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Access denied: You don't have enough privileges")

    return UserDetailSchemas.from_orm(user)


@router_users.put("/{user_uuid}", response_model=UserDetailSchemas, status_code=status.HTTP_200_OK)
async def update_user(user_uuid: UUID,
                      objects: UserUpdate,
                      current_user: User = Depends(get_current_user),
                      db: AsyncSession = Depends(get_db)):
    logger.info("Попытка изменения данных пользователя с UUID: %s", user_uuid)

    user = await db.scalar(
        select(User)
        .options(selectinload(User.roles))
        .where(User.roles.has(title="USER"), User.uuid == user_uuid)
    )
    if "SUPERUSER" not in [role.name for role in current_user.roles] and user_uuid != current_user.uuid:
        logger.error("Доступ запрещен: У вас недостаточно прав")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Access denied: You don't have enough privileges")

    if user is None:
        logger.error("Пользователь c UUID: %s не найден", user_uuid)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    existing_user = await db.scalar(
        select(User)
        .where(User.email == objects.email,
               User.phone_number == objects.phone_number,
               User.uuid == user_uuid)
    )

    if existing_user:
        if existing_user.email == objects.email:
            logger.error("Пользователь с email: %s уже существует", objects.email)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"User with this email already exist")
        if existing_user.phone_number == objects.phone_number:
            logger.error("Пользователь с номером телефона: %s уже существует", objects.phone_number)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="User with this phone number already exist")

    for var, value in objects.dict(exclude_unset=True).items():
        setattr(user, var, value)

    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.success("Пользователь с UUID: %s успешно обновлен", user_uuid)
    return UserDetailSchemas.from_orm(user)


@router_users.delete("/{user_uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_uuid: UUID,
                      current_user: User = Depends(get_current_user),
                      db: AsyncSession = Depends(get_db)):
    logger.info("Попытка удаления пользователя с UUID: %s", user_uuid)

    user = await db.scalar(
        select(User)
        .options(selectinload(User.roles))
        .where(User.roles.has(title="USER"), User.uuid == user_uuid)
    )

    if "SUPERUSER" not in [role.name for role in current_user.roles] and user_uuid != current_user.uuid:
        logger.error("Доступ запрещен: У вас недостаточно прав")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Access denied: You don't have enough privileges")
    if user is None:
        logger.error("Пользователь c UUID: %s не найден", user_uuid)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    await db.delete(user)
    await db.commit()

    logger.success("Пользователь: c UUID: %s успешно удален", user_uuid)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
