from fastapi import APIRouter

from languages.routes import router_translation
from src.superusers.router import router_admin
from src.authorization.router import router_auth
from src.users.router import router_users
from src.payments.router import router_payment
from src.couriers.router import router_couriers
from src.restaurant_owners.router import router_restaurant_owner

routes = APIRouter()

# Регистрация роутера для админа
routes.include_router(router_admin)

# Регистрация роутера для авторизации
routes.include_router(router_auth)

# Регистрация роутера для пользователей
routes.include_router(router_users)

# Регистрация роутера для курьеров
routes.include_router(router_couriers)

# Регистрация роутера для регистрации карты
# routes.include_router(router_payment)

# Регистрация роутера для владельцев ресторанов
routes.include_router(router_restaurant_owner)

# Регистрация роутера для языков
routes.include_router(router_translation)
