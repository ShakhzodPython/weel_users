from slowapi import Limiter
from slowapi.util import get_remote_address

# Создаем ограничитель скорости и Limiter, используя IP-адрес в качестве ключа.
limiter = Limiter(key_func=get_remote_address)
