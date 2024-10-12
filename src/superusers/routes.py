import jwt
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Form, Response, status

from sqlalchemy import asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from config.settings import SECRET_KEY, ALGORITHM
from config.security import get_api_key, create_access_token, create_refresh_token, is_superuser
from logs.logger import logger
from config.database import get_db
from src.superusers.schemas import SuperuserSchemas, SuperuserUpdate, RolesSchemas
from src.superusers.utils import validate_password, validate_username
from src.authorization.utils import check_phone
from src.users.models import User, Role

router_admin = APIRouter(
    tags=["Administration"]
)


@router_admin.post("/api/v1/auth/superusers/sign_up/", status_code=status.HTTP_201_CREATED)
async def sign_up(username: str = Form(...),
                  password: str = Form(...),
                  api_key: str = Depends(get_api_key),
                  db: AsyncSession = Depends(get_db)):
    logger.info("Попытка создания администратора с именем пользователя: %s", username)

    role = await db.scalar(select(Role).where(Role.name == "SUPERUSER"))

    if role is None:
        logger.error("Роль с названием: SUPERUSER не найдена")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    existing_username = await db.scalar(
        select(User)
        .where(User.username == username)
    )

    if existing_username:
        logger.error("Администратор с именем пользователя: %s уже существует", username)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Superuser with this username already exist")

    new_superuser = User(username=validate_username(username), roles=[role])
    new_superuser.set_password(validate_password(password))

    db.add(new_superuser)
    await db.commit()
    await db.refresh(new_superuser)

    logger.success("Администратор с именем пользователя: %s создался успешно", username)
    return {"detail": f"Superuser with username: {username} created successfully"}


@router_admin.post("/api/v1/auth/superusers/sign_in/", status_code=status.HTTP_200_OK)
async def sign_in(username: str = Form(...),
                  password: str = Form(...),
                  db: AsyncSession = Depends(get_db)):
    logger.info("Попытка входа в аккаунт с именем пользователя: %s", username)

    superuser = await db.scalar(select(User).options(selectinload(User.roles)).where(
        User.roles.any(name="SUPERUSER"), User.username == username))

    if superuser is None or not superuser.verify_password(password):
        logger.error("Не верное имя пользователя или пароль для администратора: %s", username)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect username or password")

    access_token = create_access_token(
        data={"user_uuid": superuser.uuid, "role": superuser.roles[0].name})
    refresh_token = create_refresh_token(
        data={"user_uuid": superuser.uuid, "role": superuser.roles[0].name})

    logger.success("Администратор с именем пользователя: %s вошел в аккаунт успешно", username)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "detail": f"Superuser with username: {username} logged into the account successfully"
    }


@router_admin.post("/api/v1/superusers/token/refresh/", status_code=status.HTTP_201_CREATED)
async def refresh_token(refresh_token: str,
                        db: AsyncSession = Depends(get_db)):
    logger.info("Попытка создания refresh token")

    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        superuser_uuid = payload.get("user_uuid")

        superuser_role = payload.get("role")
        if superuser_role != "SUPERUSER":
            logger.error("Роль: SUPERUSER не найдено")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    except jwt.ExpiredSignatureError:
        logger.error("Refresh token истек")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Refresh token expired")

    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token invalid")

    role = await db.scalar(select(Role).where(Role.name == "SUPERUSER"))
    new_access_token = create_access_token(data={"user_uuid": superuser_uuid, "role": role.name})

    logger.success("Токен успешно обновлён для администратора с UUID: %s", superuser_uuid)
    return {"access_token": new_access_token}


# TODO: Сделать поиск по имя пользователя администратора
@router_admin.get("/api/v1/superusers/", response_model=List[SuperuserSchemas],
                  status_code=status.HTTP_200_OK)
async def get_superusers(
        current_user: User = Depends(is_superuser),
        db: AsyncSession = Depends(get_db)):
    logger.info("Попытка получения всех администраторов")

    stmt = await db.scalars(
        select(User)
        .options(selectinload(User.roles))
        .where(User.roles.any(name="SUPERUSER"))
        .order_by(asc(User.uuid))
    )
    superusers = stmt.all()

    logger.success("Все администраторы получены успешно")
    return [SuperuserSchemas.from_orm(superuser) for superuser in superusers]


@router_admin.get("/api/v1/superusers/{superuser_uuid}/", response_model=SuperuserSchemas,
                  status_code=status.HTTP_200_OK)
async def get_superuser_by_uuid(superuser_uuid: UUID,
                                current_user: User = Depends(is_superuser),
                                db: AsyncSession = Depends(get_db)):
    logger.info("Попытка получения администратора с UUID: %s", superuser_uuid)

    if superuser_uuid != current_user.uuid:
        logger.error("Доступ запрещен: У вас недостаточно прав")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Access denied: You don't have enough privileges")

    superuser = await db.scalar(
        select(User)
        .options(selectinload(User.roles))
        .where(User.roles.any(name="SUPERUSER"), User.uuid == superuser_uuid)
    )

    if superuser is None:
        logger.error("Администратор с UUID: %s не найден", superuser_uuid)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Superuser not found")

    logger.success("Администратор с UUID: %s успешно получен", superuser_uuid)
    return SuperuserSchemas.from_orm(superuser)


@router_admin.put("/api/v1/superusers/{superuser_uuid}/", response_model=SuperuserSchemas,
                  status_code=status.HTTP_200_OK)
async def update_superuser(superuser_uuid: UUID,
                           objects: SuperuserUpdate,
                           current_user: User = Depends(is_superuser),
                           db: AsyncSession = Depends(get_db)):
    logger.info("Попытка обновления администратора с UUID: %s", superuser_uuid)

    if superuser_uuid != current_user.uuid:
        logger.error("Доступ запрещен: У вас недостаточно прав")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Access denied: You don't have enough privileges")

    superuser = await db.scalar(
        select(User)
        .options(selectinload(User.roles))
        .where(User.roles.any(name="SUPERUSER"), User.uuid == superuser_uuid)
    )

    if superuser is None:
        logger.error("Администратор с UUID: %s не найден", superuser_uuid)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Superuser not found")

    existing_superuser = await db.scalar(
        select(User)
        .where(User.email == objects.email,
               User.phone_number == objects.phone_number,
               User.uuid == superuser_uuid)
    )

    if existing_superuser:
        if existing_superuser.email == objects.email:
            logger.error("Администратор с email: %s уже существует", objects.email)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superuser with this email already exist")
        if existing_superuser.phone_number == check_phone(objects.phone_number):
            logger.error("Администратор с номером телефона: %s уже существует", objects.phone_number)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="Superuser with this phone number already exist")

    for var, value in objects.dict(exclude_unset=True).items():
        setattr(superuser, var, value)

    db.add(superuser)
    await db.commit()
    await db.refresh(superuser)

    logger.success("Администратор с UUID: %s успешно обновлен", superuser_uuid)
    return SuperuserSchemas.from_orm(superuser)


@router_admin.delete("/api/v1/superusers/{superuser_uuid}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_superuser(superuser_uuid: UUID,
                           current_user: User = Depends(is_superuser),
                           db: AsyncSession = Depends(get_db)):
    logger.info("Попытка удаления администратора с UUID: %s", superuser_uuid)

    if superuser_uuid != current_user.uuid:
        logger.error("Доступ запрещен: У вас недостаточно прав")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Access denied: You don't have enough privileges")

    superuser = await db.scalar(
        select(User)
        .options(selectinload(User.roles))
        .where(User.roles.any(name="SUPERUSER"), User.uuid == superuser_uuid)
    )

    if superuser is None:
        logger.error("Администратор с UUID: %s не найден", superuser_uuid)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Superuser not found")

    await db.delete(superuser)
    await db.commit()

    logger.success("Администратор: c UUID: %s успешно удален", superuser_uuid)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# TODO: сделать фильтры
@router_admin.get("/api/v1/roles/", response_model=List[RolesSchemas],
                  status_code=status.HTTP_200_OK)
async def get_roles(
        current_user: User = Depends(is_superuser),
        db: AsyncSession = Depends(get_db)):
    logger.info("Попытка получения всех ролей")

    stmt = await db.scalars(
        select(Role)
        .order_by(asc(Role.id))
    )

    roles = stmt.all()

    logger.success("Все роли успешно получены")
    return [RolesSchemas.from_orm(role) for role in roles]


@router_admin.get("/api/v1/roles/{role_id}/", response_model=RolesSchemas,
                  status_code=status.HTTP_200_OK)
async def get_role_by_id(role_id: int,
                         current_user: User = Depends(is_superuser),
                         db: AsyncSession = Depends(get_db)):
    logger.info("Попытка получить роль с ID: %s", role_id)

    role = await db.scalar(select(Role).where(Role.id == role_id))

    if role is None:
        logger.error("Роль с ID: %s не найдена", role_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    logger.success("Роль с ID: %s успешно получена", role_id)
    return RolesSchemas.from_orm(role)


@router_admin.post("/api/v1/roles/add/", response_model=RolesSchemas,
                   status_code=status.HTTP_201_CREATED)
async def create_role(
        name: str = Form(...),
        description: str = Form(...),
        current_user: User = Depends(is_superuser),
        db: AsyncSession = Depends(get_db)):
    logger.info("Попытка создания роли c названием: %s", name)

    existing_role = await db.scalar(select(Role).where(Role.name == name))

    if existing_role:
        logger.error("Роль с названием: %s уже существует", name)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role with this name already exist")

    new_role = Role(name=name, description=description)
    db.add(new_role)
    await db.commit()
    await db.refresh(new_role)

    logger.success("Роль с названием: %s успешно создана", name)
    return RolesSchemas.from_orm(new_role)


@router_admin.put("/api/v1/roles/{role_id}/", response_model=RolesSchemas,
                  status_code=status.HTTP_200_OK)
async def update_role(role_id: int,
                      name: str = Form(...),
                      description: str = Form(...),
                      current_user: User = Depends(is_superuser),
                      db: AsyncSession = Depends(get_db)):
    logger.info("Попытка обновить роль с ID: %s", role_id)

    role = await db.scalar(select(Role).where(Role.id == role_id))

    if role is None:
        logger.error("Роль с ID: %s не найдена", role_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    existing_role = await db.scalar(select(Role).where(Role.name == name, Role.id != role_id))

    if existing_role:
        logger.error("Роль с названием: %s уже существует", name)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role with this name already exist")

    role.name = name
    role.description = description
    await db.commit()
    await db.refresh(role)

    logger.success("Роль с ID: %s обновлено успешно", name)
    return RolesSchemas.from_orm(role)


@router_admin.delete("/api/v1/roles/{role_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(role_id: int,
                      current_user: User = Depends(is_superuser),
                      db: AsyncSession = Depends(get_db)):
    logger.info("Попытка удаления роли с ID: %s", role_id)

    role = await db.scalar(select(Role).where(Role.id == role_id))
    if role is None:
        logger.error("Роль с ID: %s не найдена", role_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    await db.delete(role)
    await db.commit()

    logger.success("Роль с ID: %s успешно удалена", role_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router_admin.put("/api/v1/users/change-role/{role_id}/", status_code=status.HTTP_200_OK)
async def change_roles(
        role_id: int,
        current_user: User = Depends(is_superuser),
        db: AsyncSession = Depends(get_db)):
    logger.info("Попытка изменить роль пользователя с UUID: %s", current_user.uuid)

    user = await db.scalar(
        select(User).options(selectinload(User.roles)).where(User.uuid == current_user.uuid)
    )

    if user.uuid != current_user.uuid:
        logger.error("Доступ запрещен: У вас недостаточно прав")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Access denied: You don't have enough privileges")

    if user is None:
        logger.error("Пользователь с UUID: %s не найден", current_user.uuid)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    role = await db.scalar(select(Role).where(Role.id == role_id))
    if role is None:
        logger.error("Роль с ID: %s не найдена", role_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    # Обновление ролей пользователя
    user.roles = [role]
    await db.commit()

    access_token = create_access_token(
        data={"user_uuid": user.uuid, "role": role.name})
    refresh_token = create_refresh_token(
        data={"user_uuid": user.uuid, "role": role.name})

    logger.success("Пользователь с UUID: %s сменил роль на %s", current_user.uuid, role.name)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "detail": f"Пользователь с ID: {current_user.uuid} сменил роль на {role.name}"
    }
