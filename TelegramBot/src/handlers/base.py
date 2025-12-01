from aiogram import Dispatcher, F
from aiogram.filters.command import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from ..keyboards import start_kb


async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    await state.clear()
    tg_id = str(message.from_user.id)
    name = message.from_user.first_name or "пользователь"

    text = (
        "Я — бот для запуска 16S-пайплайна и управления задачами анализа.\n\n"
        f"Привет, {name}!\n\n"
        "Что я умею:\n"
        "- Запуск анализа одного FASTQ-файла (/run_analysis)\n"
        "- Создание когортного отчёта из нескольких завершённых задач (/create_cohort)\n"
        "- Проверка статуса задачи (/status <task_id>)\n"
        "- Получение PDF-отчёта (/get_report <task_id>)\n"
        "- Просмотр списка ваших анализов (/list_analyses)\n\n"
        "Выберите действие или используйте команды /help и /run_analysis."
    )
    await message.answer(text, reply_markup=start_kb())


async def cmd_help(message: Message):
    """Обработчик команды /help"""
    text = (
        "Справка по командам:\n\n"
        "/start — приветствие и краткое описание.\n"
        "/help — эта справка.\n"
        "/run_analysis — запустить новый анализ (бот попросит загрузить FASTQ и выбрать параметры).\n"
        "/create_cohort — создать когортный отчёт из 10+ завершённых задач.\n"
        "/status <task_id> — посмотреть статус задачи и логи.\n"
        "/list_analyses [фильтры] — список ваших задач. Пример фильтра: /list_analyses instrument=QIIME2\n"
        "/get_report <task_id> — скачать PDF/отчёт по задаче.\n"
        "/cancel <task_id> — отменить задачу, если она в pending или running.\n\n"
        "Если нужно — свяжитесь с техподдержкой: support@example.com"
    )
    await message.answer(text)


async def callback_start_buttons(callback_query: CallbackQuery):
    """Обработчик кнопок стартового меню"""
    if callback_query.data == "start_analysis":
        await callback_query.message.answer(
            "Запустим диалог запуска анализа. Пожалуйста, используйте команду /run_analysis чтобы начать."
        )
    elif callback_query.data == "show_help":
        await callback_query.message.answer("Вызов помощи: используйте команду /help")

    await callback_query.answer()


def register_base_handlers(dp: Dispatcher):
    """Регистрация базовых хэндлеров"""
    dp.message.register(cmd_start, Command(commands=["start"]))
    dp.message.register(cmd_help, Command(commands=["help"]))
    dp.callback_query.register(callback_start_buttons, F.data.in_(["start_analysis", "show_help"]))
