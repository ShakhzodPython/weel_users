from typing import List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Query, Response, status

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from logs.logger import logger
from src.users.models import User, Card
from src.users.schemas import UserSchemas, UserUpdate
from database.security import get_api_key, get_current_user, is_superuser
from database.settings import get_db

router_users = APIRouter(
    tags=["Users"],
)


@router_users.get("/api/v1/users/", response_model=List[UserSchemas], status_code=status.HTTP_200_OK)
async def get_users(
        blacklisted_cards: bool = Query(False, description="Filter users with blacklisted credit cards"),
        current_user: User = Depends(is_superuser),
        db: AsyncSession = Depends(get_db)):
    logger.info("Попытка получения всех пользователей")

    stmt = select(User).options(selectinload(User.roles), selectinload(User.cards)).where(
        User.roles.any(
            name="USER"))  # метод any() используется для фильтрации пользователей, чтобы выбрать роль
    if blacklisted_cards == True:
        stmt = stmt.where(User.cards.any(Card.is_blacklisted == True))
    else:
        stmt = stmt.where(User.cards.any(Card.is_blacklisted == False))

    role = await db.execute(stmt)
    users = role.scalars().all()

    logger.success("Пользователи успешно получены")
    return [UserSchemas.from_orm(user) for user in users]


@router_users.get("/api/v1/users/{user_id}/", response_model=UserSchemas, status_code=status.HTTP_200_OK)
async def get_user_by_id(user_id: UUID,
                         current_user: User = Depends(get_current_user),
                         db: AsyncSession = Depends(get_db)):
    logger.info(f"Попытка получение пользователя с UUID: {user_id}")

    stmt = await db.execute(
        select(User).options(selectinload(User.roles)).where(
            User.roles.any(name="USER"), User.id == user_id))
    user = stmt.scalars().one_or_none()
    if not user:
        logger.error(f"Пользователь c UUID: {user_id} не найден")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if "SUPERUSER" not in [role.name for role in current_user.roles] and user_id != current_user.id:
        logger.error("Доступ запрещен: У вас недостаточно прав")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Access denied: You don't have enough privileges")

    return UserSchemas.from_orm(user)


@router_users.put("/api/v1/users/{user_id}/", response_model=UserSchemas, status_code=status.HTTP_200_OK)
async def update_user(user_id: UUID,
                      objects: UserUpdate,
                      current_user: User = Depends(get_current_user),
                      db: AsyncSession = Depends(get_db)):
    logger.info(f"Попытка изменения данных пользователя с UUID: {user_id}")
    stmt = await db.execute(
        select(User).options(selectinload(User.roles)).where(User.id == user_id, User.roles.any(name="USER")))
    user = stmt.scalars().one_or_none()

    if "SUPERUSER" not in [role.name for role in current_user.roles] and user_id != current_user.id:
        logger.error("Доступ запрещен: У вас недостаточно прав")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Access denied: You don't have enough privileges")

    if not user:
        logger.error(f"Пользователь c UUID: {user_id} не найден")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    existing_phone_number_stmt = await db.execute(
        select(User).where(User.phone_number == objects.phone_number, User.id != user_id))
    existing_phone_number = existing_phone_number_stmt.scalars().one_or_none()
    if existing_phone_number:
        logger.error(f"Пользователь с номером телефона: {objects.phone_number} уже существует")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User with this phone number already exist")

    existing_email_stmt = await db.execute(
        select(User).where(User.email == objects.email, User.id != user_id))
    existing_email = existing_email_stmt.scalars().one_or_none()
    if existing_email:
        logger.error(f"Пользователь с email: {objects.email} уже существует")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"User with this email already exist")

    for var, value in objects.dict(exclude_unset=True).items():
        setattr(user, var, value)

    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info(f"Пользователь с UUID: {user_id} успешно обновлен")
    return UserSchemas.from_orm(user)


@router_users.delete("/api/v1/users/{user_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: UUID,
                      current_user: User = Depends(get_current_user),
                      db: AsyncSession = Depends(get_db)):
    logger.info(f"Попытка удаления пользователя с UUID: {user_id}")
    stmt = await db.execute(
        select(User).options(selectinload(User.roles)).where(User.id == user_id, User.roles.any(name="USER")))
    user = stmt.scalars().one_or_none()

    if "SUPERUSER" not in [role.name for role in current_user.roles] and user_id != current_user.id:
        logger.error("Доступ запрещен: У вас недостаточно прав")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Access denied: You don't have enough privileges")
    if not user:
        logger.error(f"Пользователь c UUID: {user_id} не найден")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    await db.delete(user)
    await db.commit()

    logger.success(f"Пользователь: c UUID: {user_id} успешно удален")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
