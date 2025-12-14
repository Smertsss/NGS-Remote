import types
from io import BytesIO
from typing import Optional
from aiogram import Dispatcher, F, Bot
from aiogram.filters.command import Command
from aiogram.types import Message

from ..task_manage import TaskManager, TaskStatus
from ..api.models import UserResponse


async def cmd_get_report(message: Message, bot: Bot, db_user: Optional[UserResponse] = None):
    """Получение отчёта по задаче"""
    if not db_user:
        await message.answer(
            "❌ Для получения отчётов необходимо зарегистрироваться.\n"
            "Введите команду: /registration"
        )
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Использование: /get_report <task_id>")
        return

    task_id = args[1].strip()
    task_manager = TaskManager()
    t = task_manager.get(task_id)

    if not t:
        await message.answer(f"Задача {task_id} не найдена.")
        return

    if t.status != TaskStatus.COMPLETED or not t.result:
        await message.answer(f"Отчёт по задаче {task_id} ещё не готов. Текущий статус: {t.status.value}")
        return

    result = t.result
    bio = BytesIO(result.bytes)
    bio.seek(0)
    filename = result.filename
    await bot.send_document(
        chat_id=message.chat.id,
        document=types.InputFile(bio, filename=filename)
    )


def register_report_handlers(dp: Dispatcher):
    """Регистрация хэндлеров отчётов"""
    dp.message.register(cmd_get_report, Command(commands=["get_report"]))