import jwt

from typing import List
from uuid import UUID

from fastapi import APIRouter, Form, Depends, HTTPException, Response, status
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.config import SECRET_KEY, ALGORITHM
from database.security import create_access_token, create_refresh_token, is_restaurant_editor, get_api_key, is_superuser
from database.settings import get_db
from logs.logger import logger
from src.administration.utils import validate_password, validate_username
from src.restaurant_editors.schemas import RestaurantEditorSchemas, RestaurantEditorUpdate
from src.users.models import User, Role

router_restaurant_editors = APIRouter(
    tags=["Restaurant Editors"]
)


@router_restaurant_editors.post("/api/v1/auth/restaurant-editors/sign_up/", status_code=status.HTTP_201_CREATED)
async def sign_up(username: str = Form(...),
                  password: str = Form(...),
                  api_key: str = Depends(get_api_key),
                  db: AsyncSession = Depends(get_db)):
    logger.info(f"Попытка создания редактора ресторанов с именем пользователя: {username}")

    stmt = await db.execute(select(Role).where(Role.name == "RESTAURANT_EDITOR"))
    role = stmt.scalars().one_or_none()
    if role is None:
        logger.error("Роль: RESTAURANT_EDITOR не найдена")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    existing_username_stmt = await db.execute(
        select(User)
        .where(User.username == username))
    existing_username = existing_username_stmt.scalars().one_or_none()
    if existing_username:
        logger.error(f"Редактор ресторанов с именем пользователя: {username} уже существует")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Username already exist")

    new_restaurant_editor = User(username=validate_username(username), roles=[role])
    new_restaurant_editor.set_password(validate_password(password))

    db.add(new_restaurant_editor)
    await db.commit()
    await db.refresh(new_restaurant_editor)

    logger.success(f"Редактор ресторанов с именем пользователя: {username} создался успешно")
    return {"detail": f"Restaurant editor: {username} created successfully"}


@router_restaurant_editors.post("/api/v1/restaurant-editors/sign_in/",
                                status_code=status.HTTP_200_OK)
async def sign_in(username: str = Form(...),
                  password: str = Form(...),
                  db: AsyncSession = Depends(get_db)):
    logger.info(f"Попытка входа в аккаунт с именем пользователя: {username}")

    stmt = await db.execute(select(User).options(selectinload(User.roles)).where(
        User.roles.any(name="RESTAURANT_EDITOR"), User.username == username))
    restaurant_editor = stmt.scalars().one_or_none()

    if restaurant_editor is None or not restaurant_editor.verify_password(password):
        logger.error(f"Не верное имя пользователя или пароль")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect username or password")

    access_token = create_access_token(
        data={"user_id": restaurant_editor.id, "role": restaurant_editor.roles[0].name})
    refresh_token = create_refresh_token(
        data={"user_id": restaurant_editor.id, "role": restaurant_editor.roles[0].name})

    logger.success(f"Редактор ресторанов с именем пользователя: {username} вошел в аккаунт успешно")
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "detail": f"Restaurant editor: {username} logged into the account successfully"
    }


@router_restaurant_editors.post("/api/v1/restaurant-editors/token/refresh/", status_code=status.HTTP_201_CREATED)
async def refresh_token(refresh_token: str,
                        api_key: str = Depends(get_api_key),
                        db: AsyncSession = Depends(get_db)):
    logger.info("Попытка создания refresh token")

    try:
        payload = jwt.decode(jwt=refresh_token, key=SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        restaurant_editor_role = payload.get("role")

        if restaurant_editor_role != "RESTAURANT_EDITOR":
            logger.error("Роль: RESTAURANT_EDITOR не найдена")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    except jwt.ExpiredSignatureError:
        logger.error("Refresh token истек")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Refresh token expired")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token invalid")

    stmt = await db.execute(select(Role).where(Role.name == "RESTAURANT_EDITOR"))
    role = stmt.scalars().one_or_none()

    new_access_token = create_access_token(data={"user_id": user_id, "role": role.name})
    logger.success(f"Токен успешно обновлён для с редактор ресторанов: {user_id}")
    return {"access_token": new_access_token}


@router_restaurant_editors.get("/api/v1/restaurant-editors/", response_model=List[RestaurantEditorSchemas],
                               status_code=status.HTTP_200_OK)
async def get_restaurant_editors(
        current_user: User = Depends(is_superuser),
        db: AsyncSession = Depends(get_db)):
    logger.info("Попытка получения всех редакторов ресторана")

    stmt = await db.execute(
        select(User).options(selectinload(User.roles)).where(User.roles.any(name="RESTAURANT_EDITOR")))
    restaurant_editors = stmt.scalars().all()
    logger.success("Все редакторы получены успешно")
    return [RestaurantEditorSchemas.from_orm(restaurant_editor) for restaurant_editor in restaurant_editors]


@router_restaurant_editors.get("/api/v1/restaurant-editors/{restaurant_editor_id}/",
                               response_model=RestaurantEditorSchemas,
                               status_code=status.HTTP_200_OK)
async def get_restaurant_editor_by_id(restaurant_editor_id: UUID,
                                      current_user: User = Depends(is_restaurant_editor),
                                      db: AsyncSession = Depends(get_db)):
    logger.info(f"Попытка получить редактора ресторана с UUID: {restaurant_editor_id}")

    if "SUPERUSER" not in [role.name for role in current_user.roles] and current_user.id != restaurant_editor_id:
        logger.error("Доступ запрещен: У вас недостаточно прав")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Access denied: You don't have enough privileges")

    stmt = await db.execute(
        select(User).options(selectinload(User.roles)).where(User.id == restaurant_editor_id,
                                                             User.roles.any(name="RESTAURANT_EDITOR")))
    restaurant_editor = stmt.scalars().one_or_none()

    if restaurant_editor is None:
        logger.error(f"Редактор ресторана c UUID: {restaurant_editor_id} не найден")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant editor not found")

    logger.success(f"Редактор ресторана с UUID: {restaurant_editor_id} получен успешно")
    return RestaurantEditorSchemas.from_orm(restaurant_editor)


@router_restaurant_editors.put("/api/v1/restaurant-editors/{restaurant_editor_id}/",
                               response_model=RestaurantEditorSchemas,
                               status_code=status.HTTP_200_OK)
async def update_restaurant_editor(restaurant_editor_id: UUID,
                                   objects: RestaurantEditorUpdate,
                                   current_user: User = Depends(is_restaurant_editor),
                                   db: AsyncSession = Depends(get_db)):
    logger.info(f"Попытка обновить редактора ресторана с UUID: {restaurant_editor_id}")

    if "SUPERUSER" not in [role.name for role in current_user.roles] and restaurant_editor_id != current_user.id:
        logger.error("Доступ запрещен: У вас недостаточно прав")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Access denied: You don't have enough privileges")

    stmt = await db.execute(select(User).options(selectinload(User.roles)).where(
        User.roles.any(name="RESTAURANT_EDITOR"), User.id == restaurant_editor_id))
    restaurant_editor = stmt.scalars().one_or_none()

    if restaurant_editor is None:
        logger.error(f"Редактор ресторана c UUID: {restaurant_editor_id} не найден")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Restaurant editor not found")

    existing_email_stmt = await db.execute(
        select(User).where(User.email == objects.email, User.id != restaurant_editor_id))
    existing_email = existing_email_stmt.scalars().one_or_none()

    existing_phone_number_stmt = await db.execute(
        select(User).where(User.phone_number == objects.phone_number, User.id != restaurant_editor_id))
    existing_phone_number = existing_phone_number_stmt.scalars().one_or_none()

    if existing_email:
        logger.error(f"Редактор ресторана с email: {objects.email} уже существует")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"Restaurant editor with this email already exist")
    elif existing_phone_number:
        logger.error(f"Редактор ресторана с номером телефона: {objects.phone_number} уже существует")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Restaurant editor with this phone number already exist")
    else:
        for var, value in objects.dict(exclude_unset=True).items():
            setattr(restaurant_editor, var, value)

    db.add(restaurant_editor)
    await db.commit()
    await db.refresh(restaurant_editor)
    logger.success(f"Редактор ресторана c UUID: {restaurant_editor_id} успешно обновлен")
    return RestaurantEditorSchemas.from_orm(restaurant_editor)


@router_restaurant_editors.delete("/api/v1/restaurant-editors/{restaurant_editor_id}/",
                                  status_code=status.HTTP_204_NO_CONTENT)
async def restaurant_editor_delete(restaurant_editor_id: UUID,
                                   current_user: User = Depends(is_restaurant_editor),
                                   db: AsyncSession = Depends(get_db)):
    logger.info(f"Попытка удаления редактора ресторана с UUID: {restaurant_editor_id}")

    if "SUPERUSER" not in [role.name for role in current_user.roles] and restaurant_editor_id != current_user.id:
        logger.error("Доступ запрещен: У вас недостаточно прав")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Access denied: You don't have enough privileges")

    stmt = await db.execute(select(User).where(User.id == restaurant_editor_id))
    restaurant_editor = stmt.scalars().one_or_none()

    if restaurant_editor is None:
        logger.error(f"Редактора ресторана c UUID: {restaurant_editor_id} не найден")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    await db.delete(restaurant_editor)
    await db.commit()
    logger.success(f"Курьер c UUID: {restaurant_editor_id} успешно удален")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
