from fastapi_filter.contrib.sqlalchemy import Filter

from src.users.models import User


class UsersFilter(Filter):
    class Constants(Filter.Constants):
        model = User
        search_field_name = "search"
        search_model_fields = ["phone_number"]
