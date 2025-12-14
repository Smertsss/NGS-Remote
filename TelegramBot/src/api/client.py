import asyncio
import logging
import httpx
import json
from typing import Optional, Dict, Any
from TelegramBot.config import AUTH_SERVICE_URL, API_TIMEOUT, API_RETRY_ATTEMPTS, API_RETRY_DELAY
from ..api.models import UserCreate, UserResponse, ErrorResponse

logger = logging.getLogger(__name__)


class AuthServiceError(Exception):
    """Базовое исключение для ошибок сервиса авторизации"""
    pass


class UserNotFoundError(AuthServiceError):
    """Пользователь не найден"""
    pass


class AuthServiceClient:
    """Клиент для работы с сервисом авторизации"""

    def __init__(self):
        self.base_url = AUTH_SERVICE_URL.rstrip('/')
        self.client = httpx.AsyncClient(
            timeout=API_TIMEOUT,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "TelegramBot/1.0"
            }
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    async def _make_request(
            self,
            method: str,
            endpoint: str,
            **kwargs
    ) -> httpx.Response:
        """Выполняет HTTP-запрос с повторными попытками"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        for attempt in range(API_RETRY_ATTEMPTS):
            try:
                response = await self.client.request(method, url, **kwargs)
                return response
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                if attempt == API_RETRY_ATTEMPTS - 1:
                    logger.error(f"Failed to connect to auth service after {API_RETRY_ATTEMPTS} attempts: {e}")
                    raise AuthServiceError(f"Cannot connect to auth service: {e}")
                logger.warning(f"Attempt {attempt + 1} failed, retrying in {API_RETRY_DELAY}s...")
                await asyncio.sleep(API_RETRY_DELAY)

    async def get_user_by_chat_id(self, chat_id: int) -> Optional[UserResponse]:
        try:
            logger.info(f"GET request to /users/{chat_id}")
            response = await self._make_request("GET", f"/users/{chat_id}")
            logger.info(f"Response status for user {chat_id}: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                logger.info(f"User data received for {chat_id}: {data}")
                return UserResponse(**data)
            elif response.status_code == 404:
                logger.info(f"User {chat_id} not found (404)")
                return None
            else:
                error_data = response.json() if response.text else {}
                logger.error(f"Unexpected status for user {chat_id}: {response.status_code}, Error: {error_data}")
                return None

        except httpx.HTTPError as e:
            logger.error(f"HTTP error while getting user {chat_id}: {e}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error getting user {chat_id}: {e}")
            return None

    async def create_user(self, user_data: UserCreate) -> UserResponse:
        try:
            json_data = user_data.dict(exclude_none=True)
            logger.info(f"Sending POST request to create user: {json_data}")

            response = await self._make_request(
                "POST",
                "/users/",
                json=json_data
            )

            logger.info(f"Response status: {response.status_code}")

            if response.status_code == 201:
                response_data = response.json()
                logger.info(f"User created successfully: {response_data}")
                return UserResponse(**response_data)
            else:
                error_data = response.json()
                logger.error(f"Failed to create user. Status: {response.status_code}, Error: {error_data}")

                error_detail = error_data.get('detail', '')
                error_detail_str = str(error_detail).lower()

                if 'уже существует' in error_detail_str or 'already exists' in error_detail_str:
                    raise AuthServiceError(f"Пользователь с chat_id {user_data.chat_id} уже существует")
                elif 'chat_id' in error_detail_str and 'required' in error_detail_str:
                    # Специальная обработка ошибки поля chat_id
                    raise AuthServiceError("Ошибка: сервер ожидает поле 'chat_id' (snake_case)")
                else:
                    raise AuthServiceError(f"Ошибка при создании пользователя: {error_detail}")

        except httpx.HTTPError as e:
            logger.error(f"HTTP error while creating user: {e}")
            raise AuthServiceError(f"Ошибка сети: {e}")
        except json.JSONDecodeError as e:
            logger.error(
                f"JSON decode error: {e}, response text: {response.text if 'response' in locals() else 'No response'}")
            raise AuthServiceError("Некорректный ответ от сервера авторизации")
        except Exception as e:
            logger.exception(f"Unexpected error in create_user: {e}")
            raise AuthServiceError(f"Неизвестная ошибка: {e}")

    async def get_or_create_user(
            self,
            chat_id: int,
            name: Optional[str] = None,
            username: Optional[str] = None,
            telegram_username: Optional[str] = None
    ) -> UserResponse:
        # Пытаемся получить пользователя
        user = await self.get_user_by_chat_id(chat_id)

        if user:
            logger.info(f"User {chat_id} already exists")
            return user

        # Создаём нового пользователя
        logger.info(f"Creating new user with chat_id {chat_id}")
        user_create = UserCreate(
            chat_id=chat_id,
            name=name,
            username=username,
            telegram_username=telegram_username
        )

        return await self.create_user(user_create)


# Singleton для удобного использования
_auth_client_instance: Optional[AuthServiceClient] = None


async def get_auth_client() -> AuthServiceClient:
    """Получает экземпляр AuthServiceClient (singleton)"""
    global _auth_client_instance

    if _auth_client_instance is None:
        _auth_client_instance = AuthServiceClient()

    return _auth_client_instance