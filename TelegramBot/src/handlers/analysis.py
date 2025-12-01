import asyncio
import logging
from aiogram import Dispatcher, F, types, Bot
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext

from ..states import RunAnalysisStates
from ..task_manage import TaskManager
from ..keyboards import tool_kb, reference_kb, clustering_kb, confirm_kb
from ..utils.analysis_simulator import simulate_analysis_and_generate_report

logger = logging.getLogger(__name__)


async def cmd_run_analysis(message: types.Message, state: FSMContext):
    """Начало диалога запуска анализа"""
    await state.set_state(RunAnalysisStates.waiting_fastq)
    await message.answer(
        "Запуск нового анализа: загрузите FASTQ (или архив FASTQ) в виде файла (прикрепите документ).",
        reply_markup=types.ReplyKeyboardRemove()
    )


async def handle_fastq_upload(message: types.Message, state: FSMContext):
    """Обработка загрузки FASTQ файла"""
    if not message.document:
        await message.answer("Пожалуйста, пришлите файл как документ (не фото).")
        return

    doc = message.document
    try:
        owner = str(message.from_user.id)
        local_path = f"uploads/{owner}_{doc.file_name}"
        await message.document.download(destination_file=local_path)
    except Exception as e:
        logger.exception("Ошибка при сохранении файла")
        await message.answer("Не удалось сохранить файл. Попробуйте ещё раз.")
        return

    await state.update_data(uploaded_file=local_path, filename=doc.file_name)
    await state.set_state(RunAnalysisStates.waiting_tool)
    await message.answer("Файл принят. Выберите инструмент анализа:", reply_markup=tool_kb())


async def callback_tool_ref_cluster(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработка выбора инструмента, референса и кластеризации"""
    data = callback_query.data or ""

    if data.startswith("tool:"):
        tool = data.split(":", 1)[1]
        await state.update_data(instrument=tool)
        await state.set_state(RunAnalysisStates.waiting_reference)
        await callback_query.message.edit_text(
            f"Выбран инструмент: {tool}\nВыберите референсную базу:",
            reply_markup=reference_kb()
        )
        await callback_query.answer()

    elif data.startswith("ref:"):
        ref = data.split(":", 1)[1]
        await state.update_data(reference=ref)
        await state.set_state(RunAnalysisStates.waiting_clustering)
        await callback_query.message.edit_text(
            f"Выбрана база: {ref}\nВыберите тип кластеризации:",
            reply_markup=clustering_kb()
        )
        await callback_query.answer()

    elif data.startswith("cluster:"):
        cluster = data.split(":", 1)[1]
        await state.update_data(clustering=cluster)
        data_all = await state.get_data()

        summary = (
            f"Параметры для запуска:\n"
            f"- Файл: {data_all.get('filename')}\n"
            f"- Инструмент: {data_all.get('instrument')}\n"
            f"- База: {data_all.get('reference')}\n"
            f"- Кластеризация: {data_all.get('clustering')}\n\n"
            "Подтвердите запуск анализа."
        )

        await state.set_state(RunAnalysisStates.confirm)
        await callback_query.message.edit_text(summary, reply_markup=confirm_kb())
        await callback_query.answer()

    elif data == "run_cancel":
        await state.clear()
        await callback_query.message.edit_text("Запуск анализа отменён.")
        await callback_query.answer()


async def callback_confirm_run(callback_query: types.CallbackQuery, bot: Bot, state: FSMContext, dp: Dispatcher):
    """Подтверждение запуска анализа"""
    data_all = await state.get_data()
    owner = str(callback_query.from_user.id)
    filename = data_all.get("filename", "uploaded.fastq")

    params = {
        "instrument": data_all.get("instrument"),
        "reference": data_all.get("reference"),
        "clustering": data_all.get("clustering")
    }

    file_path = data_all.get("uploaded_file")
    task_manager = TaskManager()
    task_id = task_manager.create_task(owner, filename, params, file_path=file_path)

    task_manager.add_log(task_id, "Задача создана пользователем.")
    await callback_query.message.edit_text(
        f"Задача создана. Task ID: {task_id}\nСтатус: pending. Вам придёт уведомление по завершению."
    )
    await callback_query.answer()

    # запуск фоновой обработки с передачей dp
    bg = asyncio.create_task(simulate_analysis_and_generate_report(task_id, bot, dp))
    task_manager.store_bg_task(task_id, bg)
    await state.clear()


def register_analysis_handlers(dp: Dispatcher):
    """Регистрация хэндлеров анализа"""
    dp.message.register(cmd_run_analysis, Command(commands=["run_analysis"]))
    dp.message.register(handle_fastq_upload, F.document, RunAnalysisStates.waiting_fastq)
    dp.callback_query.register(
        callback_tool_ref_cluster,
        F.data.startswith(("tool:", "ref:", "cluster:", "run_cancel"))
    )
    dp.callback_query.register(callback_confirm_run, F.data == "confirm_run")
