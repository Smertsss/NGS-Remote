import asyncio
import logging
import signal
import sys
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from TelegramBot.config import TOKEN
from src.handlers import register_all_handlers
from src.task_manage import TaskManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def on_shutdown(dp: Dispatcher, bot: Bot):
    """Функция для корректного завершения работы"""
    logger.info("Завершение работы бота...")

    # Отменяем все фоновые задачи
    task_manager = TaskManager()
    logger.info(f"Отмена фоновых задач... Всего задач: {len(task_manager._bg_tasks)}")

    for task_id, bg_task in task_manager._bg_tasks.items():
        if not bg_task.done():
            bg_task.cancel()
            logger.info(f"Отменена задача: {task_id}")

    # Ждем завершения всех задач
    if task_manager._bg_tasks:
        await asyncio.gather(*task_manager._bg_tasks.values(), return_exceptions=True)

    # Закрываем сессию бота
    await bot.session.close()
    logger.info("Бот завершил работу")


async def main():
    bot = Bot(token=TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Регистрация всех хэндлеров
    register_all_handlers(dp)

    # Обработка сигналов завершения
    def signal_handler():
        logger.info("Получен сигнал завершения")
        asyncio.create_task(on_shutdown(dp, bot))
        sys.exit(0)

    # Регистрация обработчиков сигналов
    signal.signal(signal.SIGINT, lambda s, f: signal_handler())
    signal.signal(signal.SIGTERM, lambda s, f: signal_handler())

    logger.info("Bot started")
    try:
        await dp.start_polling(bot)
    finally:
        await on_shutdown(dp, bot)


if __name__ == "__main__":
    asyncio.run(main())