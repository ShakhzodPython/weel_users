from typing import List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Query, Response, status
from sqlalchemy import asc, exists, not_

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from logs.logger import logger
from src.users.models import User, Card
from src.users.schemas import UserSchemas, UserUpdate
from database.security import get_current_user, is_superuser
from database.settings import get_db

router_users = APIRouter(
    tags=["Users"],
)


# TODO: сделать поиск по username
@router_users.get("/api/v1/users/", response_model=List[UserSchemas],
                  status_code=status.HTTP_200_OK)
async def get_users(
        blacklisted_cards: bool = Query(False, description="Filter users with blacklisted credit cards"),
        current_user: User = Depends(is_superuser),
        db: AsyncSession = Depends(get_db)):
    logger.info("Попытка получения всех пользователей")

    # метод any() используется для фильтрации пользователей, чтобы выбрать роль
    stmt = (
        select(User)
        .options(selectinload(User.roles), selectinload(User.cards))
        .where(User.roles.any(name="USER"))
        .order_by(asc(User.uuid))
    )
    # TODO: понять как работает !!!
    if blacklisted_cards == True:
        stmt = stmt.where(
            exists().where(
                (Card.user_id == User.uuid) & (Card.is_blacklisted == True)
            )
        )
    else:
        stmt = stmt.where(
            not_(
                exists().where(
                    (Card.user_id == User.uuid) & (Card.is_blacklisted == True)
                )
            )
        )

    role = await db.scalars(stmt)
    users = role.all()

    logger.success("Пользователи успешно получены")
    return [UserSchemas.from_orm(user) for user in users]


@router_users.get("/api/v1/users/{user_uuid}/", response_model=UserSchemas, status_code=status.HTTP_200_OK)
async def get_user_by_uuid(user_uuid: UUID,
                           current_user: User = Depends(get_current_user),
                           db: AsyncSession = Depends(get_db)):
    logger.info("Попытка получение пользователя с UUID: %s", user_uuid)

    user = await db.scalar(
        select(User)
        .options(selectinload(User.roles))
        .where(User.roles.any(name="USER"), User.uuid == user_uuid)
    )

    if user is None:
        logger.error("Пользователь c UUID: %s не найден", user_uuid)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if "SUPERUSER" not in [role.name for role in current_user.roles] and user_uuid != current_user.uuid:
        logger.error("Доступ запрещен: У вас недостаточно прав")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Access denied: You don't have enough privileges")

    return UserSchemas.from_orm(user)


@router_users.put("/api/v1/users/{user_uuid}/", response_model=UserSchemas, status_code=status.HTTP_200_OK)
async def update_user(user_uuid: UUID,
                      objects: UserUpdate,
                      current_user: User = Depends(get_current_user),
                      db: AsyncSession = Depends(get_db)):
    logger.info("Попытка изменения данных пользователя с UUID: %s", user_uuid)
    user = await db.scalar(
        select(User)
        .options(selectinload(User.roles))
        .where(User.roles.any(name="USER"), User.uuid == user_uuid)
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
    return UserSchemas.from_orm(user)


@router_users.delete("/api/v1/users/{user_uuid}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_uuid: UUID,
                      current_user: User = Depends(get_current_user),
                      db: AsyncSession = Depends(get_db)):
    logger.info("Попытка удаления пользователя с UUID: %s", user_uuid)
    user = await db.scalar(
        select(User)
        .options(selectinload(User.roles))
        .where(User.roles.any(name="USER"), User.uuid == user_uuid)
    )

    if "SUPERUSER" not in [role.name for role in current_user.roles] and user_uuid != current_user.uuid:
        logger.error("Доступ запрещен: У вас недостаточно прав")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Access denied: You don't have enough privileges")
    if not user:
        logger.error("Пользователь c UUID: %s не найден", user_uuid)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    await db.delete(user)
    await db.commit()

    logger.success("Пользователь: c UUID: %s успешно удален", user_uuid)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
