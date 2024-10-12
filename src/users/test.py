import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from main import app
from src.users.models import User



# Фикстура — это особая функция в библиотеке pytest, которая позволяет подготовить
# необходимые данные или окружение для тестов.
# Фикстуры могут использоваться для создания временных данных,
# настройки окружения, подключения к базе данных,
# или, как в данном случае, для создания мокированного объекта для тестирования.

# Фикстура для мокированного пользователя
@pytest.fixture
def mock_user():
    """
    Создаёт объект пользователя
    для использования в тестах.
    Этот пользователь имеет заданный UUID,
    номер телефона и другие атрибуты.
    """

    user = User(
        uuid="efdb6be5-1d62-4925-9f32-b0705b6eb9a3",
        full_name=None,
        phone_number="909170775",
        email=None,
        registered_at="2024-10-04T12:01:21.339191"
    )
    user.roles = []
    user.cards = []
    return user


# Фикстура для мокированной сессии базы данных
@pytest.fixture
async def mock_db_session(mock_user):
    """
    Создаёт мокированную сессию базы данных
    для использования в тестах.
    Возвращает мокированную сессию,
    в которой используется объект пользователя mock_user.
    """

    # Создаём мок сессии базы данных, которая соответствует спецификации AsyncSession
    mock_session = AsyncMock(spec=AsyncSession)

    # Настраиваем результат выполнения scalars().all(), чтобы возвращать список, содержащий mock_user
    mock_scalars = AsyncMock()
    mock_scalars.all.return_value = [mock_user]
    mock_session.scalars.return_value = mock_scalars
    return mock_session


# Фикстура для мокированной функции получения сессии базы данных
@pytest.fixture
async def mock_get_db(mock_db_session):
    """
    Создаёт мокированную функцию для получения
    сессии базы данных.
    Используется для того, чтобы заменить
    реальную функцию получения сессии в тестах.
    """
    async def get_db():
        yield await mock_db_session

    return get_db


# Тестовая функция для получения определенного пользователя из базы данных
@pytest.mark.asyncio
async def test_get_users(mock_get_db):
    with patch("src.users.routes.get_db", await mock_get_db):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get("/api/v1/users/")

            expected_data = [
                {
                    "uuid": "efdb6be5-1d62-4925-9f32-b0705b6eb9a3",
                    "full_name": None,
                    "phone_number": "909170775",
                    "email": None,
                    "registered_at": "2024-10-04T12:01:21.339191",
                    "cards": []
                }
            ]

            assert response.status_code == 200
            assert response.json() == expected_data
    print(f"RESPONSE ---------------- {response.json()} -------------- ")
