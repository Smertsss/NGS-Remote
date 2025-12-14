import logging
from datetime import datetime
from io import BytesIO
from typing import Optional
from aiogram import Dispatcher, F, types, Bot
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext

from ..states import CreateCohortStates
from ..task_manage import TaskManager, TaskStatus
from ..api.models import UserResponse

logger = logging.getLogger(__name__)


async def cmd_create_cohort(message: types.Message, state: FSMContext, db_user: Optional[UserResponse] = None):
    """Начало создания когорты"""
    if not db_user:
        await message.answer(
            "❌ Для создания когорты необходимо зарегистрироваться.\n"
            "Введите команду: /registration"
        )
        return

    await message.answer(
        "Создание когорты: отправьте список task_id через запятую (минимум 10 задач), которые нужно объединить в когортный отчёт.\n"
        "Пример: taskid1,taskid2,taskid3,..."
    )
    await state.set_state(CreateCohortStates.waiting_task_list)


async def handle_cohort_task_list(message: types.Message, state: FSMContext, bot: Bot,
                                  db_user: Optional[UserResponse] = None):
    """Обработка списка задач для когорты"""
    if not db_user:
        await message.answer("❌ Пользователь не авторизован.")
        return

    raw = message.text.strip()
    ids = [s.strip() for s in raw.split(",") if s.strip()]

    if len(ids) < 10:
        await message.answer("Нужно выбрать минимум 10 задач для когорты.")
        await state.clear()
        return

    # проверка задач
    task_manager = TaskManager()
    tasks = []
    for tid in ids:
        t = task_manager.get(tid)
        if not t:
            await message.answer(f"Задача {tid} не найдена. Отмена создания когорты.")
            await state.clear()
            return
        if t.status != TaskStatus.COMPLETED:
            await message.answer(
                f"Задача {tid} не завершена (статус {t.status}). Когорта требует завершённых задач. Отмена.")
            await state.clear()
            return
        tasks.append(t)

    # генерация объединённого отчёта
    combined = BytesIO()
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        c = canvas.Canvas(combined, pagesize=letter)
        for t in tasks:
            c.setFont("Helvetica", 12)
            c.drawString(72, 720, f"Cohort report - Task {t.id}")
            c.drawString(72, 700, f"Sample file: {t.filename}")
            c.drawString(72, 680, f"Params: {t.params}")
            c.drawString(72, 640, "Aggregated metrics (simulated)")
            c.showPage()
        c.save()
        combined.seek(0)
        filename = f"cohort_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        await bot.send_document(chat_id=message.chat.id, document=types.InputFile(combined, filename=filename))
        await message.answer("Когортный отчёт создан и отправлен.")
    except Exception as e:
        logger.exception("Ошибка при создании когортного отчёта")
        await message.answer("Не удалось создать PDF-отчёт (не установлен reportlab).")

    await state.clear()


def register_cohort_handlers(dp: Dispatcher):
    """Регистрация хэндлеров когорт"""
    dp.message.register(cmd_create_cohort, Command(commands=["create_cohort"]))
    dp.message.register(handle_cohort_task_list, CreateCohortStates.waiting_task_list)