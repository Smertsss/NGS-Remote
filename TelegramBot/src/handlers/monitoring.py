from aiogram import Dispatcher, F
from aiogram.filters.command import Command
from aiogram.types import Message

from ..task_manage import TaskManager, TaskStatus


async def cmd_status(message: Message):
    """Проверка статуса задачи"""
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Использование: /status <task_id>")
        return

    task_id = args[1].strip()
    task_manager = TaskManager()
    t = task_manager.get(task_id)

    if not t:
        await message.answer(f"Задача {task_id} не найдена.")
        return

    text = (
        f"Task ID: {t.id}\n"
        f"Статус: {t.status.value}\n"
        f"Файл: {t.filename}\n"
        f"Параметры: instrument={t.params.get('instrument')}, reference={t.params.get('reference')}, clustering={t.params.get('clustering')}\n"
        f"Создана: {t.created_at.isoformat()}\n"
    )

    if t.started_at:
        text += f"Начата: {t.started_at.isoformat()}\n"
    if t.finished_at:
        text += f"Завершена: {t.finished_at.isoformat()}\n"

    logs = t.log[-10:]
    if logs:
        text += "\nЛоги (последние):\n" + "\n".join(logs)

    await message.answer(text)


async def cmd_list_analyses(message: Message):
    """Список задач с фильтрацией"""
    args = message.text.split(maxsplit=1)
    filters = {}

    if len(args) > 1:
        raw = args[1]
        for part in raw.split():
            if "=" in part:
                k, v = part.split("=", 1)
                filters[k] = v

    owner = str(message.from_user.id)
    task_manager = TaskManager()
    tasks = task_manager.list_for_user(owner, filters=filters)

    if not tasks:
        await message.answer("У вас нет задач, соответствующих фильтру.")
        return

    lines = []
    for t in sorted(tasks, key=lambda x: x.created_at, reverse=True)[:50]:
        lines.append(f"{t.id[:8]}... | {t.filename} | {t.params.get('instrument')} | {t.status.value}")

    await message.answer("Ваши задачи:\n" + "\n".join(lines))


async def cmd_cancel(message: Message):
    """Отмена задачи"""
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Использование: /cancel <task_id>")
        return

    task_id = args[1].strip()
    task_manager = TaskManager()
    t = task_manager.get(task_id)

    if not t:
        await message.answer(f"Задача {task_id} не найдена.")
        return

    if t.status in (TaskStatus.PENDING, TaskStatus.RUNNING):
        task_manager.cancel_task(task_id)
        await message.answer(f"Задача {task_id} была отменена.")
    else:
        await message.answer(f"Задачу {task_id} нельзя отменить в статусе {t.status.value}.")


def register_monitoring_handlers(dp: Dispatcher):
    """Регистрация хэндлеров мониторинга"""
    dp.message.register(cmd_status, Command(commands=["status"]))
    dp.message.register(cmd_list_analyses, Command(commands=["list_analyses"]))
    dp.message.register(cmd_cancel, Command(commands=["cancel"]))
