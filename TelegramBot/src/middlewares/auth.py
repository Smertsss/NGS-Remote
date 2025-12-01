from typing import Callable, Dict, Any, Awaitable, Optional
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update, Message, CallbackQuery
import logging

from ..api.client import get_auth_client, AuthServiceError
from ..api.models import UserResponse

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseMiddleware):
    """Мидлварь для проверки пользователя"""

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any]
    ) -> Any:
        # Проверяем, что это обновление с пользователем
        if isinstance(event, Update):
            # Получаем пользователя из обновления
            user = None
            if event.message:
                user = event.message.from_user
            elif event.callback_query:
                user = event.callback_query.from_user
            elif event.edited_message:
                user = event.edited_message.from_user
            # Добавьте другие типы сообщений по необходимости

            if not user:
                logger.debug("Update without from_user - skipping auth check")
                return await handler(event, data)
        else:
            # Если это не Update, пропускаем
            return await handler(event, data)

        logger.info(f"Processing user: {user.id}, username: {user.username}")

        try:
            auth_client = await get_auth_client()
            logger.info(f"Auth client initialized, checking user {user.id}")

            # Пытаемся получить пользователя по chat_id
            db_user = await auth_client.get_user_by_chat_id(user.id)

            if db_user:
                data['db_user'] = db_user
                logger.info(f"✅ User found in DB: {db_user.id} (chat_id: {db_user.chat_id})")
            else:
                data['db_user'] = None
                logger.info(f"❌ User NOT found in DB for chat_id: {user.id}")

        except AuthServiceError as e:
            logger.error(f"Auth service error for user {user.id}: {e}")
            data['db_user'] = None

        except Exception as e:
            logger.exception(f"Unexpected auth error for user {user.id}: {e}")
            data['db_user'] = None

        logger.info(f"Calling handler with db_user: {'Yes' if data.get('db_user') else 'No'}")
        return await handler(event, data)