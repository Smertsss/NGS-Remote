import logging
from typing import Optional
from aiogram import Dispatcher, F
from aiogram.filters.command import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from ..keyboards import start_kb, registration_kb
from ..api.models import UserResponse, UserCreate
from ..api.client import get_auth_client, AuthServiceError

logger = logging.getLogger(__name__)


async def cmd_start(message: Message, state: FSMContext, db_user: Optional[UserResponse] = None):
    """Обработчик команды /start"""
    await state.clear()

    user = message.from_user
    name = user.first_name or "пользователь"

    if db_user:
        # Пользователь уже зарегистрирован
        welcome_name = db_user.name or name

        text = (
            "Я — бот для запуска 16S-пайплайна и управления задачами анализа.\n\n"
            f"Привет, {welcome_name}!\n"
            "Что я умею:\n"
            "- Запуск анализа одного FASTQ-файла (/run_analysis)\n"
            "- Создание когортного отчёта из нескольких завершённых задач (/create_cohort)\n"
            "- Проверка статуса задачи (/status <task_id>)\n"
            "- Получение PDF-отчёта (/get_report <task_id>)\n"
            "- Просмотр списка ваших анализов (/list_analyses)\n\n"
            "Выберите действие или используйте команды /help и /run_analysis."
        )
        await message.answer(text, reply_markup=start_kb())
    else:
        # Пользователь не зарегистрирован
        text = (
            "👋 Добро пожаловать!\n\n"
            f"Привет, {name}!\n"
            "Для использования бота вам необходимо зарегистрироваться.\n\n"
            "Вы хотите зарегистрироваться сейчас?"
        )
        await message.answer(text, reply_markup=registration_kb())


async def cmd_registration(message: Message, state: FSMContext):
    """Обработчик команды /registration"""
    await state.clear()

    user = message.from_user

    try:
        auth_client = await get_auth_client()

        # Создаем данные пользователя
        user_data = UserCreate(
            chat_id=user.id,
            name=user.first_name or f"User_{user.id}",
            username=user.username or f"user_{user.id}",
            telegram_username=user.username
        )

        logger.info(f"Creating user with data: {user_data.dict()}")

        # Отправляем POST запрос на создание пользователя
        new_user = await auth_client.create_user(user_data)

        logger.info(f"User created successfully: {new_user}")

        await message.answer(
            f"✅ Регистрация прошла успешно!\n\n"
            f"Ваши данные:\n"
            f"ID в системе: {new_user.id}\n"
            f"Chat ID: {new_user.chat_id}\n"
            f"Имя: {new_user.name or 'Не указано'}\n"
            f"Юзернейм: {new_user.telegram_username or 'Не указан'}\n\n"
            f"Теперь вы можете использовать все возможности бота.\n"
            f"Введите /start для начала работы."
        )

    except AuthServiceError as e:
        error_msg = str(e)
        logger.error(f"Auth service error during registration: {error_msg}")

        # Проверяем, не зарегистрирован ли пользователь уже
        if "уже существует" in error_msg.lower() or "already exists" in error_msg.lower():
            await message.answer(
                "ℹ️ Вы уже зарегистрированы!\n"
                "Используйте /start для начала работы."
            )
        else:
            await message.answer(
                f"❌ Ошибка при регистрации: {error_msg}\n"
                f"Пожалуйста, попробуйте позже или обратитесь в поддержку."
            )

    except Exception as e:
        logger.exception(f"Unexpected error during registration: {e}")
        await message.answer(
            "❌ Произошла непредвиденная ошибка при регистрации.\n"
            "Пожалуйста, попробуйте позже или обратитесь в поддержку."
        )


async def cmd_help(message: Message, db_user: Optional[UserResponse] = None):
    """Обработчик команды /help"""
    text = (
        "Справка по командам:\n\n"
        "/start — приветствие и начало работы\n"
        "/registration — регистрация в системе\n"
        "/help — эта справка\n"
        "/run_analysis — запустить новый анализ (бот попросит загрузить FASTQ и выбрать параметры)\n"
        "/create_cohort — создать когортный отчёт из 10+ завершённых задач\n"
        "/status <task_id> — посмотреть статус задачи и логи\n"
        "/list_analyses [фильтры] — список ваших задач. Пример фильтра: /list_analyses instrument=QIIME2\n"
        "/get_report <task_id> — скачать PDF/отчёт по задаче\n"
        "/cancel <task_id> — отменить задачу, если она в pending или running\n\n"
    )

    text += "Если нужно — свяжитесь с техподдержкой: support@example.com"

    await message.answer(text)


async def callback_registration_confirm(callback_query: CallbackQuery):
    """Обработчик подтверждения регистрации"""
    logger.info(f"Registration callback: {callback_query.data}")

    if callback_query.data == "reg_confirm":
        await callback_query.message.edit_text(
            "🔄 Регистрация начата...\n"
            "Пожалуйста, подождите."
        )

        # Запускаем процесс регистрации
        user = callback_query.from_user

        try:
            auth_client = await get_auth_client()

            user_data = UserCreate(
                chat_id=user.id,
                name=user.first_name or f"User_{user.id}",
                username=user.username or f"user_{user.id}",
                telegram_username=user.username
            )

            logger.info(f"Creating user via callback: {user_data.dict()}")

            new_user = await auth_client.create_user(user_data)

            await callback_query.message.edit_text(
                f"✅ Регистрация прошла успешно!\n\n"
                f"Теперь введите /start для начала работы."
            )

        except AuthServiceError as e:
            error_msg = str(e)
            logger.error(f"Registration error in callback: {error_msg}")

            if "уже существует" in error_msg.lower() or "already exists" in error_msg.lower():
                await callback_query.message.edit_text(
                    "ℹ️ Вы уже зарегистрированы!\n"
                    "Используйте /start для начала работы."
                )
            else:
                await callback_query.message.edit_text(
                    f"❌ Ошибка при регистрации: {error_msg}\n"
                    f"Попробуйте команду /registration позже."
                )

        except Exception as e:
            logger.exception(f"Unexpected error in registration callback: {e}")
            await callback_query.message.edit_text(
                "❌ Произошла ошибка при регистрации.\n"
                "Пожалуйста, попробуйте команду /registration позже."
            )

    elif callback_query.data == "reg_cancel":
        await callback_query.message.edit_text(
            "❌ Регистрация отменена.\n"
            "Вы можете зарегистрироваться позже, используя команду /registration"
        )

    await callback_query.answer()


async def callback_start_buttons(callback_query: CallbackQuery, db_user: Optional[UserResponse] = None):
    """Обработчик кнопок стартового меню"""
    if not db_user:
        await callback_query.answer(
            "Для использования бота необходимо зарегистрироваться.\n"
            "Введите команду: /registration",
            show_alert=True
        )
        return

    if callback_query.data == "start_analysis":
        await callback_query.message.answer(
            "Запустим диалог запуска анализа. Пожалуйста, используйте команду /run_analysis чтобы начать."
        )
    elif callback_query.data == "show_help":
        await callback_query.message.answer("Вызов помощи: используйте команду /help")

    await callback_query.answer()


async def cmd_status_check(message: Message, db_user: Optional[UserResponse] = None):
    """Проверка статуса пользователя (для отладки)"""
    user = message.from_user

    text = (
        f"👤 Статус пользователя:\n"
        f"Telegram ID: {user.id}\n"
        f"Имя: {user.first_name}\n"
        f"Юзернейм: {user.username}\n"
        f"---\n"
        f"В базе данных: {'✅ Да' if db_user else '❌ Нет'}\n"
    )

    if db_user:
        text += (
            f"ID в системе: {db_user.id}\n"
            f"Chat ID в базе: {db_user.chat_id}\n"
            f"Имя в базе: {db_user.name or 'Не указано'}\n"
            f"Юзернейм в базе: {db_user.username or 'Не указан'}\n"
        )

    await message.answer(text)


def register_base_handlers(dp: Dispatcher):
    """Регистрация базовых хэндлеров"""
    logger.info("Registering base handlers...")

    dp.message.register(cmd_start, Command(commands=["start"]))
    dp.message.register(cmd_registration, Command(commands=["registration"]))
    dp.message.register(cmd_help, Command(commands=["help"]))
    dp.message.register(cmd_status_check, Command(commands=["status_check"]))
    dp.callback_query.register(callback_registration_confirm, F.data.in_(["reg_confirm", "reg_cancel"]))
    dp.callback_query.register(callback_start_buttons, F.data.in_(["start_analysis", "show_help"]))

    logger.info("Base handlers registered")