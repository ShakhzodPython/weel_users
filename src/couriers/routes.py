import os
import jwt

from typing import List
from uuid import UUID

from fastapi import APIRouter, Form, Depends, HTTPException, Response, status, File, UploadFile
from sqlalchemy import asc, or_
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config.settings import SECRET_KEY, ALGORITHM, UPLOAD_DIR
from config.security import create_access_token, create_refresh_token, is_superuser
from config.database import get_db
from logs.logger import logger
from src.superusers.utils import validate_password, validate_username
from src.authorization.utils import check_phone
from src.couriers.schemas import CourierSchemas, CourierUpdate
from src.media.models import Media
from src.media.utils import save_image
from src.users.models import User, Role

router_couriers = APIRouter(
    tags=["Couriers"]
)


@router_couriers.post("/api/v1/auth/couriers/sign_up/", response_model=CourierSchemas,
                      status_code=status.HTTP_201_CREATED)
async def sign_up(username: str = Form(...),
                  password: str = Form(...),
                  full_name: str = Form(...),
                  phone_number: str = Form(...),
                  image: UploadFile = File(...),
                  current_user: User = Depends(is_superuser),
                  db: AsyncSession = Depends(get_db)):
    logger.info("Попытка создания курьера с именем пользователя: %s", username)

    role = await db.scalar(select(Role).where(Role.name == "COURIER"))
    if role is None:
        logger.error("Роль: COURIER не найдена")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    existing_user = await db.scalar(
        select(User)
        .where(
            or_(
                User.username == username,
                User.phone_number == phone_number
            )
        )
    )
    if existing_user:
        if existing_user.username == username:
            logger.error("Курьер с именем пользователя: %s уже существует", username)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="Courier with this username already exist")
        if existing_user.phone_number == phone_number:
            logger.error("Курьер с телефон номером: %s уже существует", phone_number)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="Courier with this phone number already exist")

    try:
        url = await save_image(image)
    except Exception as e:
        logger.error("Ошибка при сохранении изображения: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save image"
        )

    new_media = Media(
        url=url,
        filename=image.filename
    )
    db.add(new_media)
    await db.flush()

    new_courier = User(
        username=validate_username(username),
        full_name=full_name,
        phone_number=await check_phone(phone_number),
        image=new_media.id,
        roles=[role])
    new_courier.set_password(validate_password(password))

    db.add(new_courier)
    await db.commit()
    await db.refresh(new_courier)

    logger.success("Курьер с именем пользователя: %s создался успешно", username)
    return CourierSchemas.from_orm(new_courier)


@router_couriers.post("/api/v1/auth/couriers/sign_in/", status_code=status.HTTP_200_OK)
async def sign_in(username: str = Form(...),
                  password: str = Form(...),
                  db: AsyncSession = Depends(get_db)):
    logger.info("Попытка входа в аккаунт с именем пользователя: %s", username)

    courier = await db.scalar(
        select(User).
        options(selectinload(User.roles))
        .where(User.roles.any(name="COURIER"), User.username == username)
    )

    if courier is None or not courier.verify_password(password):
        logger.error("Не верное имя пользователя или пароль")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect username or password")

    access_token = create_access_token(
        data={"user_uuid": courier.uuid, "role": courier.roles[0].name})
    refresh_token = create_refresh_token(
        data={"user_uuid": courier.uuid, "role": courier.roles[0].name})

    logger.success("Курьер с именем пользователя: %s успешно вошел в аккаунт", username)
    return {
        "uuid": str(courier.uuid),
        "access_token": access_token,
        "refresh_token": refresh_token,
        "detail": f"Courier with username: {username} logged into the account successfully"
    }


@router_couriers.post("/api/v1/couriers/token/refresh/", status_code=status.HTTP_201_CREATED)
async def refresh_token(refresh_token: str,
                        db: AsyncSession = Depends(get_db)):
    logger.info("Попытка создания refresh token")

    try:
        payload = jwt.decode(jwt=refresh_token, key=SECRET_KEY, algorithms=[ALGORITHM])
        user_uuid = payload.get("user_uuid")
        courier_role = payload.get("role")

        if courier_role != "COURIER":
            logger.error("Роль: COURIER не найдена")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    except jwt.ExpiredSignatureError:
        logger.error("Refresh token истек")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Refresh token expired")
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token invalid")

    role = await db.scalar(select(Role).where(Role.name == "COURIER"))

    new_access_token = create_access_token(data={"user_uuid": user_uuid, "role": role.name})
    logger.success("Токен успешно обновлён для курьера с UUID: %s", user_uuid)
    return {"access_token": new_access_token}


# TODO: сделать поиск по имя пользователя
@router_couriers.get("/api/v1/couriers/", response_model=List[CourierSchemas],
                     status_code=status.HTTP_200_OK)
async def get_couriers(
        # username: str = Query(None),
        # current_user: User = Depends(is_superuser),
        db: AsyncSession = Depends(get_db)):
    logger.info("Попытка получения всех курьеров")

    stmt = await db.scalars(
        select(User)
        .options(selectinload(User.media), selectinload(User.roles))
        .where(User.roles.any(name="COURIER"))
        .order_by(asc(User.uuid))
    )
    couriers = stmt.all()

    logger.success("Все курьеры получены успешно")
    return [CourierSchemas.from_orm(courier) for courier in couriers]


@router_couriers.get("/api/v1/couriers/{user_uuid}/", response_model=CourierSchemas,
                     status_code=status.HTTP_200_OK)
async def get_courier_by_uuid(user_uuid: UUID,
                              current_user: User = Depends(is_superuser),
                              db: AsyncSession = Depends(get_db)):
    logger.info("Попытка получение курьера с UUID: %s", user_uuid)

    if "SUPERUSER" not in [role.name for role in current_user.roles] and current_user.uuid != user_uuid:
        logger.error("Доступ запрещен: У вас недостаточно прав")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Access denied: You don't have enough privileges")

    courier = await db.scalar(
        select(User)
        .options(selectinload(User.roles),
                 selectinload(User.media))
        .where(User.roles.any(name="COURIER"), User.uuid == user_uuid))

    if courier is None:
        logger.error("Курьер c UUID: %s не найден", user_uuid)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Courier not found")

    logger.success("Курьер с UUID: %s получен успешно", user_uuid)
    return CourierSchemas.from_orm(courier)


@router_couriers.put("/api/v1/couriers/{user_uuid}/", response_model=CourierSchemas, status_code=status.HTTP_200_OK)
async def update_courier(user_uuid: UUID,
                         objects: CourierUpdate,
                         current_user: User = Depends(is_superuser),
                         db: AsyncSession = Depends(get_db)):
    logger.info("Попытка обновить курьера с UUID: %s", user_uuid)

    if "SUPERUSER" not in [role.name for role in current_user.roles] and user_uuid != current_user.uuid:
        logger.error("Доступ запрещен: У вас недостаточно прав")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Access denied: You don't have enough privileges")

    courier = await db.scalar(
        select(User)
        .options(selectinload(User.roles))
        .where(User.roles.any(name="COURIER"), User.uuid == user_uuid)
    )

    if courier is None:
        logger.error("Курьер c UUID: %s не найден", user_uuid)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Courier not found")

    existing_courier = await db.scalar(
        select(User)
        .where(User.email == objects.email,
               User.phone_number == objects.phone_number,
               User.uuid == user_uuid)
    )

    if existing_courier:
        if existing_courier.email == objects.email:
            logger.error("Курьер с email: %s уже существует", objects.email)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Courier with this email already exist")
        if existing_courier.phone_number == check_phone(objects.phone_number):
            logger.error("Курьер с номером телефона: %s уже существует", objects.phone_number)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="Courier with this phone number already exist")

    for var, value in objects.dict(exclude_unset=True).items():
        setattr(courier, var, value)

    db.add(courier)
    await db.commit()
    await db.refresh(courier)

    logger.success("Курьер c UUID: %s успешно обновлен", user_uuid)
    return CourierSchemas.from_orm(courier)


@router_couriers.delete("/api/v1/couriers/{user_uuid}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_courier(user_uuid: UUID,
                         current_user: User = Depends(is_superuser),
                         db: AsyncSession = Depends(get_db)):
    logger.info("Попытка удаления курьера с UUID: %s", user_uuid)

    if "SUPERUSER" not in [role.name for role in current_user.roles] and user_uuid != current_user.uuid:
        logger.error("Доступ запрещен: У вас недостаточно прав")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Access denied: You don't have enough privileges")

    courier = await db.scalar(
        select(User)
        .options(selectinload(User.roles), selectinload(User.media))
        .where(User.roles.any(name="COURIER"), User.uuid == user_uuid)
    )

    if courier is None:
        logger.error("Курьер c UUID: не найден", user_uuid)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    try:
        if courier.media:
            media = courier.media
            url = os.path.join(UPLOAD_DIR, os.path.basename(media.url))
            if os.path.exists(url):
                try:
                    os.remove(url)
                except Exception as e:
                    logger.error("Ошибка при удалении файла медиа: %s", str(e))
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to delete media file")
            await db.delete(media)

        await db.delete(courier)
        await db.commit()
        logger.success("Курьер c UUID: успешно удален", user_uuid)
    except Exception as e:
        logger.error("Ошибка: %s при удалении курьера с UUID: %s", user_uuid, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
