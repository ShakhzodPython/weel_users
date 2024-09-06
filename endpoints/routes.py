from fastapi import APIRouter

from src.authorization.routes import router_auth
from src.administration.routes import router_admin
from src.couriers.routes import router_couriers
from src.payments.routes import router_payment
from src.users.routes import router_users

routes = APIRouter()

# Регистрация роутера для админа
routes.include_router(router_admin)

# Регистрация роутера для курьеров
routes.include_router(router_couriers)

# Регистрация роутера для авторизации
routes.include_router(router_auth)

# Регистрация роутера для пользователей
routes.include_router(router_users)

# Регистрация роутера для регистрации карты
routes.include_router(router_payment)
