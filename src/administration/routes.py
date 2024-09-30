import jwt
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Form, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from database.config import SECRET_KEY, ALGORITHM
from database.security import get_api_key, create_access_token, create_refresh_token, is_superuser
from logs.logger import logger
from database.settings import get_db
from src.administration.schemas import SuperuserSchemas, SuperuserUpdate
from src.administration.utils import validate_password, validate_username
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
    logger.info(f"Попытка создания администратора с именем пользователя: {username}")

    stmt = await db.execute(select(Role).where(Role.name == "SUPERUSER"))
    role = stmt.scalars().one_or_none()
    if role is None:
        logger.error("Роль: SUPERUSER не найдена")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    existing_username_stmt = await db.execute(select(User).where(User.username == username))
    existing_username = existing_username_stmt.scalars().one_or_none()
    if existing_username:
        logger.error(f"Администратор с именем пользователя: {username} уже существует")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Username already exist")

    new_superuser = User(username=validate_username(username), roles=[role])
    new_superuser.set_password(validate_password(password))

    db.add(new_superuser)
    await db.commit()
    await db.refresh(new_superuser)

    logger.success(f"Администратор с именем пользователя: {username} создался успешно")
    return {"detail": f"Administrator: {username} created successfully"}


@router_admin.post("/api/v1/auth/superusers/sign_in/", status_code=status.HTTP_200_OK)
async def sign_in(username: str = Form(...),
                  password: str = Form(...),
                  db: AsyncSession = Depends(get_db)):
    logger.info(f"Попытка входа в аккаунт с именем пользователя: {username}")

    superuser = await db.scalar(select(User).options(selectinload(User.roles)).where(
        User.roles.any(name="SUPERUSER"), User.username == username))

    if superuser is None or not superuser.verify_password(password):
        logger.error(f"Не верное имя пользователя или пароль")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect username or password")

    access_token = create_access_token(
        data={"user_id": superuser.id, "role": superuser.roles[0].name})
    refresh_token = create_refresh_token(
        data={"user_id": superuser.id, "role": superuser.roles[0].name})

    logger.success(f"Администратор с именем пользователя: {username} вошел в аккаунт успешно")
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "detail": f"Superuser: {username} logged into the account successfully"
    }


@router_admin.post("/api/v1/superusers/token/refresh/", status_code=status.HTTP_201_CREATED)
async def refresh_token(refresh_token: str,
                        db: AsyncSession = Depends(get_db)):
    logger.info("Попытка создания refresh token")

    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")

        superuser_role = payload.get("role")
        if superuser_role != "SUPERUSER":
            logger.error("Роль: SUPERUSER не найдено")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    except jwt.ExpiredSignatureError:
        logger.error("Refresh token истек")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Refresh token expired")

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token invalid")

    stmt = await db.execute(select(Role).where(Role.name == "SUPERUSER"))
    role = stmt.scalars().one_or_none()
    new_access_token = create_access_token(data={"user_id": user_id, "role": role.name})

    logger.success(f"Токен успешно обновлён для администратора с UUID: {user_id}")
    return {"access_token": new_access_token}


@router_admin.get("/api/v1/superusers/", response_model=List[SuperuserSchemas], status_code=status.HTTP_200_OK)
async def get_superusers(
        current_user: User = Depends(is_superuser),
        db: AsyncSession = Depends(get_db)):
    logger.info("Попытка получения всех администраторов")

    stmt = await db.execute(select(User).options(selectinload(User.roles)).where(User.roles.any(name="SUPERUSER")))
    superusers = stmt.scalars().all()

    logger.success("Все администраторы получены успешно")
    return [SuperuserSchemas.from_orm(superuser) for superuser in superusers]


@router_admin.get("/api/v1/superusers/{superuser_id}/", response_model=SuperuserSchemas, status_code=status.HTTP_200_OK)
async def get_superuser_by_id(superuser_id: UUID,
                              current_user: User = Depends(is_superuser),
                              db: AsyncSession = Depends(get_db)):
    logger.info(f"Попытка получения администратора с UUID: {superuser_id}")

    if superuser_id != current_user.id:
        logger.error("Доступ запрещен: У вас недостаточно прав")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Access denied: You don't have enough privileges")

    stmt = await db.execute(
        select(User).options(selectinload(User.roles)).where(User.roles.any(name="SUPERUSER"), User.id == superuser_id))
    superuser = stmt.scalars().one_or_none()

    if superuser is None:
        logger.error(f"Администратор с UUID: {superuser_id} не найден")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Superuser not found")

    logger.success(f"Администратор с UUID: {superuser_id} успешно получен")
    return SuperuserSchemas.from_orm(superuser)


@router_admin.put("/api/v1/superusers/{superuser_id}/", response_model=SuperuserSchemas, status_code=status.HTTP_200_OK)
async def update_superuser(superuser_id: UUID,
                           objects: SuperuserUpdate,
                           current_user: User = Depends(is_superuser),
                           db: AsyncSession = Depends(get_db)):
    logger.info(f"Попытка обновления администратора с UUID: {superuser_id}")

    if superuser_id != current_user.id:
        logger.error("Доступ запрещен: У вас недостаточно прав")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Access denied: You don't have enough privileges")

    stmt = await db.execute(select(User).options(selectinload(User.roles)).where(
        User.roles.any(name="SUPERUSER"), User.id == superuser_id
    ))
    superuser = stmt.scalars().one_or_none()

    if superuser is None:
        logger.error(f"Администратор с UUID: {superuser_id} не найден")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Superuser not found")

    existing_superuser_email_stmt = await db.execute(select(User).options(selectinload(User.roles)).where(
        User.roles.any(name="SUPERUSER"), User.email == objects.email, User.id != superuser_id
    ))
    existing_superuser_email = existing_superuser_email_stmt.scalars().one_or_none()

    existing_superuser_phone_number_stmt = await db.execute(select(User).options(selectinload(User.roles)).where(
        User.roles.any(name="SUPERUSER"), User.phone_number == check_phone(objects.phone_number),
                                          User.id != superuser_id
    ))
    existing_superuser_phone_number = existing_superuser_phone_number_stmt.scalars().one_or_none()

    if existing_superuser_email:
        logger.error(f"Администратор с email: {objects.email} уже существует")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superuser with this email already exist")
    elif existing_superuser_phone_number:
        logger.error(f"Администратор с номером телефона: {objects.phone_number} уже существует")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Superuser with this phone number already exist")
    else:
        for var, value in objects.dict(exclude_unset=True).items():
            setattr(superuser, var, value)

    db.add(superuser)
    await db.commit()
    await db.refresh(superuser)

    logger.success(f"Администратор с UUID: {superuser_id} успешно обновлен")
    return SuperuserSchemas.from_orm(superuser)


@router_admin.delete("/api/v1/superusers/{superuser_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_superuser(superuser_id: UUID,
                           current_user: User = Depends(is_superuser),
                           db: AsyncSession = Depends(get_db)):
    logger.info(f"Попытка удаления администратора с UUID: {superuser_id}")

    if superuser_id != current_user.id:
        logger.error("Доступ запрещен: У вас недостаточно прав")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Access denied: You don't have enough privileges")

    stmt = await db.execute(select(User).options(selectinload(User.roles)).where(
        User.roles.any(name="SUPERUSER"), User.id == superuser_id
    ))
    superuser = stmt.scalars().one_or_none()

    if superuser is None:
        logger.error(f"Администратор с UUID: {superuser_id} не найден")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Superuser not found")

    await db.delete(superuser)
    await db.commit()

    logger.success(f"Администратор: c UUID: {superuser_id} успешно удален")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router_admin.get("/api/v1/roles/", status_code=status.HTTP_200_OK)
async def get_roles(
        current_user: User = Depends(is_superuser),
        db: AsyncSession = Depends(get_db)):
    logger.info("Попытка получения всех ролей")

    stmt = await db.execute(select(Role))
    roles = stmt.scalars().all()

    logger.success("Все роли успешно получены")
    return {
        "roles": roles
    }


@router_admin.get("/api/v1/roles/{role_id}/", status_code=status.HTTP_200_OK)
async def get_role_by_id(role_id: int,
                         current_user: User = Depends(is_superuser),
                         db: AsyncSession = Depends(get_db)):
    logger.info(f"Попытка получить роль с ID: {role_id}")

    stmt = await db.execute(select(Role).where(Role.id == role_id))
    role = stmt.scalars().one_or_none()

    if role is None:
        logger.error(f"Роль с ID: {role_id} не найдена")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    logger.success(f"Роль с ID: {role_id} успешно получена")
    return {
        "role": {
            "id": role.id,
            "name": role.name,
            "description": role.description,
            "created_at": role.created_at
        }
    }


@router_admin.post("/api/v1/roles/add/", status_code=status.HTTP_201_CREATED)
async def create_role(
        name: str = Form(...),
        description: str = Form(...),
        current_user: User = Depends(is_superuser),
        db: AsyncSession = Depends(get_db)):
    logger.info(f"Попытка создания роли c названием: {name}")

    existing_role_stmt = await db.execute(select(Role).where(Role.name == name))
    existing_role = existing_role_stmt.scalars().one_or_none()

    if existing_role:
        logger.error(f"Роль с названием: {name} уже существует")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role with this name already exist")

    new_role = Role(name=name, description=description)
    db.add(new_role)
    await db.commit()
    await db.refresh(new_role)

    logger.success(f"Роль с названием: {name} успешно создана")
    return {
        "role": {
            "id": new_role.id,
            "name": name,
            "description": description,
            "created_at": new_role.created_at
        }
    }


@router_admin.put("/api/v1/roles/{role_id}/", status_code=status.HTTP_200_OK)
async def update_role(role_id: int,
                      name: str = Form(...),
                      description: str = Form(...),
                      current_user: User = Depends(is_superuser),
                      db: AsyncSession = Depends(get_db)):
    logger.info(f"Попытка обновить роль с ID: {role_id}")

    stmt = await db.execute(select(Role).where(Role.id == role_id))
    role = stmt.scalars().one_or_none()

    if role is None:
        logger.error(f"Роль с ID: {role_id} не найдена")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    existing_role_stmt = await db.execute(select(Role).where(Role.name == name, Role.id != role_id))
    existing_role = existing_role_stmt.scalars().one_or_none()

    if existing_role:
        logger.error(f"Роль с названием: {name} уже существует")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role with this name already exist")

    role.name = name
    role.description = description
    await db.commit()
    await db.refresh(role)

    logger.success(f"Роль с ID: {role_id} обновлено успешно")
    return {
        "role": {
            "id": role.id,
            "name": role.name,
            "description": role.description,
            "created_at": role.created_at

        }
    }


@router_admin.delete("/api/v1/roles/{role_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(role_id: int,
                      current_user: User = Depends(is_superuser),
                      db: AsyncSession = Depends(get_db)):
    logger.info(f"Попытка удаления роли с ID: {role_id}")

    stmt = await db.execute(select(Role).where(Role.id == role_id))
    role = stmt.scalars().one_or_none()
    if role is None:
        logger.error(f"Роль с ID: {role_id} не найдена")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    await db.delete(role)
    await db.commit()

    logger.success(f"Роль с ID: {role_id} успешно удалена")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router_admin.put("/api/v1/users/change-role/{role_id}/", status_code=status.HTTP_200_OK)
async def change_roles(
        role_id: int,
        current_user: User = Depends(is_superuser),
        db: AsyncSession = Depends(get_db)):
    logger.info(f"Попытка изменить роль пользователя с UUID: {current_user.id}")

    user_stmt = await db.execute(
        select(User).options(selectinload(User.roles)).where(User.id == current_user.id)
    )
    user = user_stmt.scalars().one_or_none()

    if user.id != current_user.id:
        logger.error("Доступ запрещен: У вас недостаточно прав")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Access denied: You don't have enough privileges")

    if user is None:
        logger.error(f"Пользователь с UUID: {current_user.id} не найден")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    stmt = await db.execute(select(Role).where(Role.id == role_id))
    role = stmt.scalars().one_or_none()

    if role is None:
        logger.error(f"Роль с ID: {role_id} не найдена")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    # Обновление ролей пользователя
    user.roles = [role]
    await db.commit()

    access_token = create_access_token(
        data={"user_id": user.id, "role": role.name})
    refresh_token = create_refresh_token(
        data={"user_id": user.id, "role": role.name})

    logger.success(f"Пользователь с UUID: {current_user.id} сменил роль на {role.name}")
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "detail": f"Пользователь с ID: {current_user.id} сменил роль на {role.name}"
    }
