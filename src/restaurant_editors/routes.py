import jwt

from typing import List
from uuid import UUID

from fastapi import APIRouter, Form, Depends, HTTPException, Response, status
from sqlalchemy import and_, asc
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

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
    logger.info("Попытка создания редактора ресторанов с именем пользователя: %s", username)

    role = await db.scalar(select(Role).where(Role.name == "RESTAURANT_EDITOR"))
    if role is None:
        logger.error("Роль: RESTAURANT_EDITOR не найдена")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    existing_username = await db.scalar(
        select(User)
        .where(User.username == username)
    )

    if existing_username:
        logger.error("Редактор ресторанов с именем пользователя: %s уже существует", username)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Username already exist")

    new_restaurant_editor = User(username=validate_username(username), roles=[role])
    new_restaurant_editor.set_password(validate_password(password))

    db.add(new_restaurant_editor)
    await db.commit()
    await db.refresh(new_restaurant_editor)

    logger.success("Редактор ресторанов с именем пользователя: %s создался успешно", username)
    return {"detail": f"Restaurant editor with username: {username} created successfully"}


@router_restaurant_editors.post("/api/v1/auth/restaurant-editors/sign_in/",
                                status_code=status.HTTP_200_OK)
async def sign_in(username: str = Form(...),
                  password: str = Form(...),
                  db: AsyncSession = Depends(get_db)):
    logger.info("Попытка входа в аккаунт с именем пользователя: %s", username)

    restaurant_editor = await db.scalar(
        select(User)
        .options(selectinload(User.roles))
        .where(and_(User.roles.any(name="RESTAURANT_EDITOR"), User.username == username))
    )

    if restaurant_editor is None or not restaurant_editor.verify_password(password):
        logger.error("Не верное имя пользователя или пароль")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect username or password")

    access_token = create_access_token(
        data={"user_uuid": restaurant_editor.uuid, "role": restaurant_editor.roles[0].name})
    refresh_token = create_refresh_token(
        data={"user_uuid": restaurant_editor.uuid, "role": restaurant_editor.roles[0].name})

    logger.success("Редактор ресторанов с именем пользователя: %s вошел в аккаунт успешно", username)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "detail": f"Restaurant editor: {username} logged into the account successfully"
    }


@router_restaurant_editors.post("/api/v1/restaurant-editors/token/refresh/", status_code=status.HTTP_201_CREATED)
async def refresh_token(refresh_token: str,
                        db: AsyncSession = Depends(get_db)):
    logger.info("Попытка создания refresh token")

    try:
        payload = jwt.decode(jwt=refresh_token, key=SECRET_KEY, algorithms=[ALGORITHM])
        user_uuid = payload.get("user_uuid")
        restaurant_editor_role = payload.get("role")

        if restaurant_editor_role != "RESTAURANT_EDITOR":
            logger.error("Роль: RESTAURANT_EDITOR не найдена")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    except jwt.ExpiredSignatureError:
        logger.error("Refresh token истек")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Refresh token expired")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token invalid")

    role = await db.scalar(select(Role).where(Role.name == "RESTAURANT_EDITOR"))

    new_access_token = create_access_token(data={"user_uuid": user_uuid, "role": role.name})
    logger.success("Токен успешно обновлён для с редактор ресторанов: %s", user_uuid)
    return {"access_token": new_access_token}


# TODO: сделать поиск по username
@router_restaurant_editors.get("/api/v1/restaurant-editors/", response_model=List[RestaurantEditorSchemas],
                               status_code=status.HTTP_200_OK)
async def get_restaurant_editors(
        current_user: User = Depends(is_superuser),
        db: AsyncSession = Depends(get_db)):
    logger.info("Попытка получения всех редакторов ресторана")

    stmt = await db.scalars(
        select(User)
        .options(selectinload(User.roles))
        .where(User.roles.any(name="RESTAURANT_EDITOR"))
        .order_by(asc(User.uuid))
    )
    restaurant_editors = stmt.all()

    logger.success("Все редакторы получены успешно")
    return [RestaurantEditorSchemas.from_orm(restaurant_editor) for restaurant_editor in restaurant_editors]


@router_restaurant_editors.get("/api/v1/restaurant-editors/{user_uuid}/",
                               response_model=RestaurantEditorSchemas,
                               status_code=status.HTTP_200_OK)
async def get_restaurant_editor_by_uuid(user_uuid: UUID,
                                        current_user: User = Depends(is_restaurant_editor),
                                        db: AsyncSession = Depends(get_db)):
    logger.info("Попытка получить редактора ресторана с UUID: %s", user_uuid)

    if "SUPERUSER" not in [role.name for role in current_user.roles] and current_user.uuid != user_uuid:
        logger.error("Доступ запрещен: У вас недостаточно прав")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Access denied: You don't have enough privileges")

    restaurant_editor = await db.scalar(
        select(User)
        .options(selectinload(User.roles))
        .where(User.roles.any(name="RESTAURANT_EDITOR"), User.uuid == user_uuid)
    )

    if restaurant_editor is None:
        logger.error("Редактор ресторана c UUID: %s не найден", user_uuid)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant editor not found")

    logger.success("Редактор ресторана с UUID: %s получен успешно", user_uuid)
    return RestaurantEditorSchemas.from_orm(restaurant_editor)


@router_restaurant_editors.put("/api/v1/restaurant-editors/{user_uuid}/",
                               response_model=RestaurantEditorSchemas,
                               status_code=status.HTTP_200_OK)
async def update_restaurant_editor(user_uuid: UUID,
                                   objects: RestaurantEditorUpdate,
                                   current_user: User = Depends(is_restaurant_editor),
                                   db: AsyncSession = Depends(get_db)):
    logger.info("Попытка обновить редактора ресторана с UUID: %s", user_uuid)

    if "SUPERUSER" not in [role.name for role in current_user.roles] and user_uuid != current_user.uuid:
        logger.error("Доступ запрещен: У вас недостаточно прав")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Access denied: You don't have enough privileges")

    restaurant_editor = await db.scalar(
        select(User)
        .options(selectinload(User.roles))
        .where(User.roles.any(name="RESTAURANT_EDITOR"), User.uuid == user_uuid)
    )

    if restaurant_editor is None:
        logger.error("Редактор ресторана c UUID: %s не найден", user_uuid)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Restaurant editor not found")

    existing_restaurant_editor = await db.scalar(
        select(User)
        .options(User.roles)
        .where(User.email == objects.email,
               User.phone_number == objects.phone_number,
               User.uuid == user_uuid)
    )

    if existing_restaurant_editor:
        if existing_restaurant_editor.email == objects.email:
            logger.error("Редактор ресторана с email: %s уже существует", objects.email)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail=f"Restaurant editor with this email already exist")
        if existing_restaurant_editor.phone_number == objects.phone_number:
            logger.error("Редактор ресторана с номером телефона: %s уже существует", objects.phone_number)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="Restaurant editor with this phone number already exist")

    for var, value in objects.dict(exclude_unset=True).items():
        setattr(restaurant_editor, var, value)

    db.add(restaurant_editor)
    await db.commit()
    await db.refresh(restaurant_editor)
    logger.success(f"Редактор ресторана c UUID: {user_uuid} успешно обновлен")
    return RestaurantEditorSchemas.from_orm(restaurant_editor)


@router_restaurant_editors.delete("/api/v1/restaurant-editors/{user_uuid}/",
                                  status_code=status.HTTP_204_NO_CONTENT)
async def restaurant_editor_delete(user_uuid: UUID,
                                   current_user: User = Depends(is_restaurant_editor),
                                   db: AsyncSession = Depends(get_db)):
    logger.info("Попытка удаления редактора ресторана с UUID: %s", user_uuid)

    if "SUPERUSER" not in [role.name for role in current_user.roles] and user_uuid != current_user.uuid:
        logger.error("Доступ запрещен: У вас недостаточно прав")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Access denied: You don't have enough privileges")

    restaurant_editor = await db.scalar(select(User).where(User.uuid == user_uuid))

    if restaurant_editor is None:
        logger.error("Редактора ресторана c UUID: %s не найден", user_uuid)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    await db.delete(restaurant_editor)
    await db.commit()
    logger.success("Редактор ресторана c UUID: %s успешно удален", user_uuid)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
