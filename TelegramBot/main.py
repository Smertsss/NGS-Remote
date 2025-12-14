import asyncio
import logging
import signal
import sys
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from TelegramBot.config import TOKEN
from src.handlers import register_all_handlers
from src.middlewares import register_middlewares
from src.task_manage import TaskManager
from src.api.client import get_auth_client

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def on_startup():
    """Действия при запуске бота"""
    logger.info("Starting bot...")

    # Проверяем подключение к сервису авторизации
    try:
        auth_client = await get_auth_client()
        test_user = await auth_client.get_user_by_chat_id(0)  # тестовый ID
        if test_user is None:
            logger.info("Auth service is accessible (test user not found - expected)")
        else:
            logger.info(f"Auth service is accessible, found test user: {test_user.id}")
    except Exception as e:
        logger.warning(f"Cannot connect to auth service on startup: {e}")
        logger.warning("Bot will continue, but auth features may not work")


async def on_shutdown(dp: Dispatcher, bot: Bot):
    """Функция для корректного завершения работы"""
    logger.info("Завершение работы бота...")

    task_manager = TaskManager()
    logger.info(f"Отмена фоновых задач... Всего задач: {len(task_manager._bg_tasks)}")

    for task_id, bg_task in task_manager._bg_tasks.items():
        if not bg_task.done():
            bg_task.cancel()
            logger.info(f"Отменена задача: {task_id}")

    if task_manager._bg_tasks:
        await asyncio.gather(*task_manager._bg_tasks.values(), return_exceptions=True)

    try:
        auth_client = await get_auth_client()
        await auth_client.client.aclose()
        logger.info("Auth client closed")
    except Exception as e:
        logger.error(f"Error closing auth client: {e}")

    await bot.session.close()
    logger.info("Бот завершил работу")


async def main():
    bot = Bot(token=TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    await register_middlewares(dp)

    register_all_handlers(dp)

    await on_startup()

    def signal_handler():
        logger.info("Получен сигнал завершения")
        asyncio.create_task(on_shutdown(dp, bot))
        sys.exit(0)

    signal.signal(signal.SIGINT, lambda s, f: signal_handler())
    signal.signal(signal.SIGTERM, lambda s, f: signal_handler())

    logger.info("Bot started")
    try:
        await dp.start_polling(bot)
    finally:
        await on_shutdown(dp, bot)


if __name__ == "__main__":
    asyncio.run(main())