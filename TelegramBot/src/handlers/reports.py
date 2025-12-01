from io import BytesIO
from aiogram import types, Dispatcher, F, Bot
from aiogram.filters.command import Command
from aiogram.types import Message

from ..task_manage import TaskManager, TaskStatus


async def cmd_get_report(message: Message, bot: Bot):
    """Получение отчёта по задаче"""
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

    bio = BytesIO(t.result.bytes)
    bio.seek(0)
    filename = t.result.filename
    await bot.send_document(
        chat_id=message.chat.id,
        document=types.InputFile(bio, filename=filename)
    )


def register_report_handlers(dp: Dispatcher):
    """Регистрация хэндлеров отчётов"""
    dp.message.register(cmd_get_report, Command(commands=["get_report"]))
