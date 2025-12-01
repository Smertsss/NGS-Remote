import os
from typing import Optional

# Токен бота
TOKEN = "8298892119:AAET3KRPYeD5B7ZH2Ffkr2mZQ0HLiFWtG4w"

# URL сервиса авторизации
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8000")

# Таймауты для HTTP-запросов
API_TIMEOUT = 30.0

# Повторные попытки при ошибках сети
API_RETRY_ATTEMPTS = 3
API_RETRY_DELAY = 1.0