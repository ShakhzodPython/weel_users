import uuid
import jwt

from datetime import datetime, timedelta

from fastapi import Header, Request, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config.database import get_db
from logs.logger import logger

from config.settings import get_settings
from src.users.models import User

settings = get_settings()


class JWTBearer(HTTPBearer):
    def __init__(self, auto_Error: bool = True):
        super(JWTBearer, self).__init__(auto_error=auto_Error,
                                        scheme_name="JWT Authorization",
                                        description="Enter the token in the format: Bearer your_access_token")

    async def __call__(self, request: Request):
        credentials: HTTPAuthorizationCredentials = await super(JWTBearer, self).__call__(request)
        if credentials:
            if not credentials.scheme == "Bearer":
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid authentication scheme.")

            token = self.verify_jwt(credentials.credentials)

            if not token["is_valid"]:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")

            if token["is_expired"]:
                raise HTTPException(status_code=status.HTTP_410_GONE, detail="Token expired")

            return credentials.credentials
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid or expired token")

    def verify_jwt(self, token: str) -> bool:
        """
        Метод проверки JWT-токена.
        Возвращает словарь с информацией о валидности
        и истечении срока действия токена.
        """
        try:
            decode_access_token(token)
            return {"is_valid": True, "is_expired": False}
        except jwt.ExpiredSignatureError:
            return {"is_valid": False, "is_expired": True}
        except jwt.PyJWTError:
            return {"is_valid": False, "is_expired": False}


def create_access_token(data: dict, expires_delta: timedelta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)):
    try:
        to_encode = data.copy()
        to_encode["user_uuid"] = str(to_encode["user_uuid"])
        expire = datetime.utcnow() + expires_delta
        to_encode.update({"exp": expire, "token_type": "access"})
        encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
        return encoded_jwt
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token invalid")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Internal server error: {str(e)}")


def create_refresh_token(data: dict, expires_delta: timedelta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)):
    try:
        to_encode = data.copy()
        to_encode["user_uuid"] = str(to_encode["user_uuid"])
        expire = datetime.utcnow() + expires_delta
        to_encode.update({"exp": expire, "token_type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
        return encoded_jwt
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token invalid")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Internal server error: {str(e)}")


def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=settings.JWT_ALGORITHM)
        user_uuid = payload.get("user_uuid")
        if not user_uuid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Token does not contain required user_uuid")

        # Преобразуем user_uuid в UUID сразу здесь, чтобы избежать дублирования кода
        payload["user_uuid"] = uuid.UUID(user_uuid)
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")


async def get_current_user(token: str = Depends(JWTBearer()),
                           db: AsyncSession = Depends(get_db)):
    payload = decode_access_token(token)

    user_uuid = payload.get("user_uuid")
    role = payload.get("role")

    user = await db.scalar(select(User).options(selectinload(User.roles)).where(User.uuid == user_uuid))

    if user is None:
        logger.error(f"Пользователь с {user_uuid} не найден")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Проверка, является ли пользователь суперпользователем
    if role == "superuser":
        return user

    return user


async def is_superuser(token: str = Depends(JWTBearer()),
                       db: AsyncSession = Depends(get_db)):
    payload = decode_access_token(token)

    user_uuid = payload.get("user_uuid")
    role = payload.get("role")

    user = await db.scalar(
        select(User)
        .options(selectinload(User.roles))
        .where(User.uuid == user_uuid)
    )

    if role != "superuser":
        logger.error("Доступ запрещен: У вас недостаточно прав")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Access denied: You don't have enough privileges")
    return user


async def is_courier(token: str = Depends(JWTBearer()),
                     db: AsyncSession = Depends(get_db)):
    payload = decode_access_token(token)

    user_uuid = payload.get("user_uuid")
    role = payload.get("role")

    user = await db.scalar(
        select(User)
        .options(selectinload(User.roles))
        .where(User.uuid == user_uuid)
    )

    if user is None:
        logger.error(f"Курьер с UUID: {user_uuid} не найден")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Courier not found")

    # Проверка, является ли пользователь суперпользователем
    if role == "superuser":
        return user
    return user


async def is_restaurant_owner(token: str = Depends(JWTBearer()),
                              db: AsyncSession = Depends(get_db)):
    payload = decode_access_token(token)
    user_uuid = payload.get("user_uuid")
    role = payload.get("role")

    user = await db.scalar(
        select(User)
        .options(selectinload(User.roles))
        .where(User.uuid == user_uuid)
    )

    if user is None:
        logger.error(f"Владелец ресторана с UUID: {user_uuid} не найден")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Owner of restaurant not found")

    # Проверка, является ли пользователь суперпользователем
    if role == "superuser":
        return user
    return user


# С помощью этой функций разработчик клиентской стороны будет должен передавать api_key в заголовках
def get_api_key(api_key: str = Header()):
    if api_key is None:
        logger.error("Вы забыли указать API_KEY")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API KEY not found")
    elif api_key != settings.API_KEY:
        logger.error("Не валидный API KEY")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid API Key")
    return api_key
