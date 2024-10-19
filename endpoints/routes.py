from fastapi import APIRouter

from languages.routes import router_translation
from src.superusers.router import router_admin
from src.authorization.router import router_auth
from src.users.router import router_users
from src.payments.router import router_payment
from src.couriers.router import router_couriers
from src.restaurants_editors.router import router_restaurants_editors

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

#
routes.include_router(router_restaurants_editors)

#
routes.include_router(router_translation)
