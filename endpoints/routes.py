from fastapi import APIRouter

from src.administration.routes import router_admin
from src.authorization.routes import router_auth
from src.users.routes import router_users
from src.payments.routes import router_payment
from src.couriers.routes import router_couriers
from src.restaurant_editors.routes import router_restaurant_editors

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
routes.include_router(router_payment)

#
routes.include_router(router_restaurant_editors)