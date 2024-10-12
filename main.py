from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from endpoints.routes import routes
from logs.filter import contextual_filter
from logs.utils import get_client_ip
from src.authorization.rate_limeter import limiter
from config.database import close_redis_connection, get_redis_connection
from config.settings import TimeMiddleware

app = FastAPI(
    title="Weel Users Microservice",
    docs_url='/',
    redoc_url=None,
    # openapi_url=None
)

# Регистрация эндпоитов
app.include_router(routes)

# Добавляем состояние лимитера к приложению
app.state.limiter = limiter

# Добавляем обработчик исключений для RateLimitExceeded
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Добавляем middleware для возвращения в ответе время запроса
app.add_middleware(TimeMiddleware)

# Добавление СORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В дальнейшем указать точные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    await get_redis_connection()


@app.middleware("http")
async def log_ip(request: Request, call_next):
    ip = get_client_ip(request)
    contextual_filter.ip = ip
    response = await call_next(request)
    return response


@app.on_event("shutdown")
async def shutdown_event():
    await close_redis_connection()


app.mount("/static", StaticFiles(directory="static"), name="static")

# @app.get("/docs", deprecated=[Depends(is_admin)])
# async def get_docs():
#     return {
#         "message": "Access to docs approved"
#     }
#
#
# @app.get("/weel-docs", include_in_schema=False, dependencies=[Depends(is_admin)])
# async def docs():
#     return app.openapi()
