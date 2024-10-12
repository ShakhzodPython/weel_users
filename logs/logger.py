import logging
import os



# Определение уровня SUCCESS
logging.addLevelName(25, "SUCCESS")


def success(self, message, *args, **kwargs):
    if self.isEnabledFor(25):
        self._log(25, message, args, **kwargs)


logging.Logger.success = success

# Настройка форматирования логов
log_format = "IP: %(ip)s | %(asctime)s.%(msecs)03d | %(levelname)s | %(name)s:%(funcName)s:%(lineno)d | Thread %(thread)d | %(message)s"
date_format = "%Y-%m-%d | %H:%M:%S"

# Проверка существования директории для логов или ее создание
log_directory = "logs"
if not os.path.exists(log_directory):
    os.makedirs(log_directory)

# Полный путь к файлу лога
log_file_path = os.path.join(log_directory, "console.log")

# Создание и настройка корневого логгера
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# Создание обработчика, который будет записывать логи в файл
file_handler = logging.FileHandler(log_file_path)
file_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))

# Создание обработчика, который будет выводить логи в консоль
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))

# Добавление обработчиков к логгеру
logger.addHandler(file_handler)
logger.addHandler(console_handler)
