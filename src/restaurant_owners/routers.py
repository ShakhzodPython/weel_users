import jwt

from uuid import UUID

from fastapi import APIRouter, Form, Depends, HTTPException, Response, Request, status
from fastapi_pagination import Page, paginate
from sqlalchemy import asc
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config.settings import get_settings
from config.security import create_access_token, create_refresh_token, get_api_key, is_restaurant_owner, is_superuser
from config.database import get_db
from languages.routes import load_translations, default_language, get_language_user
from logs.logger import logger
from src.superusers.utils import validate_password, validate_username
from src.restaurant_owners.schemas import RestaurantOwnerSchemas, RestaurantOwnerDetailSchemas, RestaurantOwnerUpdate
from src.users.models import User, Role

settings = get_settings()

router_restaurant_owner = APIRouter(
    tags=["restaurant owners"],
    # responses={404: {"description": "Not found"}},
)


@router_restaurant_owner.post("/auth/restaurant-owners/sign_up", status_code=status.HTTP_201_CREATED)
async def sign_up(username: str = Form(...),
                  password: str = Form(...),
                  api_key: str = Depends(get_api_key),
                  db: AsyncSession = Depends(get_db)):
    logger.info("Попытка создать владельца ресторана с именем пользователя: %s", username)

    role = await db.scalar(select(Role).where(Role.title == "restaurant_owner"))

    if role is None:
        logger.error("Роль: restaurant_owner не найдена")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    existing_username = await db.scalar(
        select(User)
        .where(User.username == username)
    )

    if existing_username:
        logger.error("Владелец ресторанов с именем пользователя: %s уже существует", username)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Username already exist")

    new_restaurant_owner = User(username=validate_username(username), role_id=role.id)
    new_restaurant_owner.set_password(validate_password(password))

    db.add(new_restaurant_owner)
    await db.commit()
    await db.refresh(new_restaurant_owner)

    logger.success("Владелец ресторана с именем пользователя: %s создался успешно", username)
    return {"detail": f"Restaurant owner with username: {username} created successfully"}


@router_restaurant_owner.post("/auth/restaurant-owners/sign_in",
                              status_code=status.HTTP_200_OK)
async def sign_in(
        request: Request,
        username: str = Form(...),
        password: str = Form(...),
        db: AsyncSession = Depends(get_db)):
    logger.info("Попытка входа в аккаунт с именем пользователя: %s", username)
    translations = await get_language_user(request)

    restaurant_owner = await db.scalar(
        select(User)
        .options(selectinload(User.roles))
        .where(User.roles.has(title="restaurant_owner"), User.username == username)
    )

    if restaurant_owner is None or not restaurant_owner.verify_password(password):
        logger.error("Не верное имя пользователя или пароль")
        error_msg = translations.get("re_error")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)

    access_token = create_access_token(
        data={"user_uuid": restaurant_owner.uuid, "role": restaurant_owner.roles.title})
    refresh_token = create_refresh_token(
        data={"user_uuid": restaurant_owner.uuid, "role": restaurant_owner.roles.title})

    success_msg = translations.get("re_sign_in").format(username=username)

    logger.success("Владелец ресторанов с именем пользователя: %s вошел в аккаунт успешно", username)
    return {
        "uuid": str(restaurant_owner.uuid),
        "access_token": access_token,
        "refresh_token": refresh_token,
        "detail": success_msg
    }


@router_restaurant_owner.post("/auth/restaurant-owners/token/refresh", status_code=status.HTTP_201_CREATED)
async def refresh_token(refresh_token: str = Form(...),
                        db: AsyncSession = Depends(get_db)):
    logger.info("Попытка создания refresh token")

    try:
        payload = jwt.decode(refresh_token, settings.JWT_SECRET, algorithms=settings.JWT_ALGORITHM)
        user_uuid = payload.get("user_uuid")
        role = payload.get("role")

        if role != "restaurant_owner":
            logger.error("Роль: restaurant_owner не найдена")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    except jwt.ExpiredSignatureError:
        logger.error("Refresh token истек")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Refresh token expired")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token invalid")

    restaurant_owner_role = await db.scalar(select(Role).where(Role.title == "restaurant_owner"))

    access_token = create_access_token(data={"user_uuid": user_uuid, "role": restaurant_owner_role.title})

    logger.success("Токен успешно обновлён для с владельца ресторанов: %s", user_uuid)
    return {"access_token": access_token}


# TODO: сделать поиск по username
@router_restaurant_owner.get("/restaurant-owners/", response_model=Page[RestaurantOwnerSchemas],
                             status_code=status.HTTP_200_OK)
async def get_restaurant_owners(
        current_user: User = Depends(is_superuser),
        db: AsyncSession = Depends(get_db)):
    logger.info("Попытка получения всех редакторов ресторана")

    stmt = await db.scalars(
        select(User)
        .options(selectinload(User.roles))
        .where(User.roles.has(title="restaurant_owner"))
        .order_by(asc(User.uuid))
    )
    restaurant_owners = stmt.all()

    logger.success("Все редакторы получены успешно")
    return paginate(restaurant_owners)


@router_restaurant_owner.get("/restaurant-owners/{user_uuid}", response_model=RestaurantOwnerDetailSchemas,
                             status_code=status.HTTP_200_OK)
async def get_restaurant_owners_by_uuid(user_uuid: UUID,
                                        current_user: User = Depends(is_restaurant_owner),
                                        db: AsyncSession = Depends(get_db)):
    logger.info("Попытка получить владельца ресторанов с UUID: %s", user_uuid)

    if current_user != "superuser" and current_user.uuid != user_uuid:
        logger.error("Доступ запрещен: У вас недостаточно прав")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Access denied: You don't have enough privileges")

    restaurant_owner = await db.scalar(
        select(User)
        .options(selectinload(User.media),
                 selectinload(User.roles))
        .where(User.roles.has(title="restaurant_owner"), User.uuid == user_uuid)
    )

    if restaurant_owner is None:
        logger.error("Владелец ресторана c UUID: %s не найден", user_uuid)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant owner not found")

    logger.success("Владелец ресторана с UUID: %s получен успешно", user_uuid)
    return RestaurantOwnerDetailSchemas.from_orm(restaurant_owner)


@router_restaurant_owner.put("/restaurant-owners/{user_uuid}",
                             response_model=RestaurantOwnerSchemas,
                             status_code=status.HTTP_200_OK)
async def update_restaurant_owner(user_uuid: UUID,
                                  objects: RestaurantOwnerUpdate,
                                  current_user: User = Depends(is_restaurant_owner),
                                  db: AsyncSession = Depends(get_db)):
    logger.info("Попытка обновить владельца ресторана с UUID: %s", user_uuid)

    if current_user != "superuser" and current_user.uuid != user_uuid:
        logger.error("Доступ запрещен: У вас недостаточно прав")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Access denied: You don't have enough privileges")

    restaurant_owner = await db.scalar(
        select(User)
        .options(selectinload(User.roles))
        .where(User.roles.has(title="restaurant_owner"), User.uuid == user_uuid)
    )

    if restaurant_owner is None:
        logger.error("Владелец ресторана c UUID: %s не найден", user_uuid)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Restaurant owner not found")

    existing_restaurant_owner = await db.scalar(
        select(User)
        .options(User.roles)
        .where(User.email == objects.email,
               User.phone_number == objects.phone_number,
               User.uuid == user_uuid)
    )

    if existing_restaurant_owner:
        if existing_restaurant_owner.email == objects.email:
            logger.error("Владелец ресторана с email: %s уже существует", objects.email)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail=f"Restaurant owner with this email already exist")
        if existing_restaurant_owner.phone_number == objects.phone_number:
            logger.error("Владелец ресторана с номером телефона: %s уже существует", objects.phone_number)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="Restaurant owner with this phone number already exist")

    for var, value in objects.dict(exclude_unset=True).items():
        setattr(restaurant_owner, var, value)

    db.add(restaurant_owner)
    await db.commit()
    await db.refresh(restaurant_owner)
    logger.success(f"Владелец ресторана c UUID: {user_uuid} успешно обновлен")
    return RestaurantOwnerSchemas.from_orm(restaurant_owner)


@router_restaurant_owner.delete("/restaurant-owners/{user_uuid}",
                                status_code=status.HTTP_204_NO_CONTENT)
async def restaurant_owner_delete(user_uuid: UUID,
                                  current_user: User = Depends(is_restaurant_owner),
                                  db: AsyncSession = Depends(get_db)):
    logger.info("Попытка удаления владельца ресторана с UUID: %s", user_uuid)

    if current_user != "superuser" and current_user.uuid != user_uuid:
        logger.error("Доступ запрещен: У вас недостаточно прав")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Access denied: You don't have enough privileges")

    restaurant_owner = await db.scalar(select(User).where(User.uuid == user_uuid))

    if restaurant_owner is None:
        logger.error("Владелец ресторана c UUID: %s не найден", user_uuid)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    await db.delete(restaurant_owner)
    await db.commit()

    logger.success("Владелец ресторана c UUID: %s успешно удален", user_uuid)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
