import hashlib
import uuid
import jwt

from datetime import datetime, timedelta

from fastapi import Header, Depends, Request
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.settings import get_db
from logs.logger import logger

from database.config import SECRET_KEY, ALGORITHM, API_KEY
from src.users.models import User


class JWTBearer(HTTPBearer):
    def __init__(self, auto_Error: bool = True):
        super(JWTBearer, self).__init__(auto_error=auto_Error,
                                        scheme_name="JWT Authorization",
                                        description="Введите токен в формате: Bearer ваш_access_token")

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


def hash_data(data, salt="some_salt"):
    """Хеширование данных с использованием SHA-256 и солью."""
    return hashlib.sha256((data + salt).encode()).hexdigest()


def create_access_token(data: dict, expires_delta: timedelta = timedelta(minutes=60)):
    try:
        to_encode = data.copy()
        to_encode['user_id'] = str(to_encode['user_id'])
        expire = datetime.utcnow() + expires_delta
        to_encode.update({"exp": expire, "token_type": "access"})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token invalid")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Internal server error: {str(e)}")


def create_refresh_token(data: dict, expires_delta: timedelta = timedelta(days=180)):
    try:
        to_encode = data.copy()
        to_encode['user_id'] = str(to_encode['user_id'])
        expire = datetime.utcnow() + expires_delta
        to_encode.update({"exp": expire, "token_type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token invalid")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Internal server error: {str(e)}")


def decode_access_token(token: str):
    try:
        payload = jwt.decode(jwt=token, key=SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Token does not contain required user_id")

        # Преобразуем user_id в UUID сразу здесь, чтобы избежать дублирования кода
        payload["user_id"] = uuid.UUID(user_id)
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")


async def get_current_user(token: str = Depends(JWTBearer()),
                           db: AsyncSession = Depends(get_db)):
    payload = decode_access_token(token)
    user_id = payload.get("user_id")

    stmt = await db.execute(select(User).options(selectinload(User.roles)).where(User.id == user_id))
    user = stmt.scalars().one_or_none()

    if not user:
        logger.error(f"Пользователь с {user_id} не найден")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Проверка, является ли пользователь суперпользователем
    if any(role.name == "SUPERUSER" for role in user.roles):
        return user
    return user


async def is_superuser(token: str = Depends(JWTBearer()),
                       db: AsyncSession = Depends(get_db)):
    payload = decode_access_token(token)

    role = payload.get("role")
    if role != "SUPERUSER":
        logger.error("Доступ запрещен: У вас недостаточно прав")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Access denied: You don't have enough privileges")
    return await get_current_user(token, db)


async def is_courier(token: str = Depends(JWTBearer()),
                     db: AsyncSession = Depends(get_db)):
    payload = decode_access_token(token)
    user_id = payload.get("user_id")
    stmt = await db.execute(select(User).options(selectinload(User.roles)).where(User.id == user_id))
    user = stmt.scalars().one_or_none()

    if not user:
        logger.error(f"Пользователь с {user_id} не найден")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Courier not found")

    # Проверка, является ли пользователь суперпользователем
    if any(role.name == "SUPERUSER" for role in user.roles):
        return user
    return user


# С помощью этой функций разработчик клиентской стороны будет должен передавать api_key в заголовках
def get_api_key(api_key: str = Header(None)):
    if api_key is None:
        logger.error("Вы забыли указать API_KEY")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API KEY not found")
    elif api_key != API_KEY:
        logger.error("Не валидный API KEY")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid API Key")
    return api_key
