import pytest

from fastapi.testclient import TestClient

from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from main import app
from src.users.models import User, Card

client = TestClient(app)


@pytest.fixture
def mock_get_db():
    """
    @pytest.fixture: Декоратор говорит pytest, что эта функция является фикстурой.
    Фикстуры — это специальные функции, которые могут подготавливать тестовое окружение,
    передавать необходимые данные или объекты для тестов, а также проводить очистку после завершения тестов.
    """
    mock_session = AsyncMock(AsyncSession)
    yield mock_session


# Тест для получения все пользователей
@pytest.mark.asyncio
async def test_get_users(mock_get_db):
    mock_user = User(uuid="db02f9bf-065e-4da9-a2de-69ed24642edg", fullname="Test User",
                     phone_number="900230023")
    mock_user.roles = [{"name": "USER"}]
    mock_user.cards = [{"is_blacklisted": False}]

    mock_get_db.scalars.return_value.all.return_value = [mock_user]

    with patch("path.to.get_db", return_value=mock_get_db):
        with patch("path.to.is_superuser", return_value=mock_user):
            response = client.get("/api/v1/users/")

            assert response.status_code == 200
            assert response.json() == [
                {
                    "uuid": "db02f9bf-065e-4da9-a2de-69ed24642edg",
                    "full_name": "Test User",
                    "phone_number": "900230023",
                    "roles": [{"name": "USER"}],
                    "cards": [{"is_blacklisted": False}]
                }
            ]
