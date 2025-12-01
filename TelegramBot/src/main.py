
"""
Вот логика бота (User stories, acceptance criteria и use-cases).
[Вставлены ваши Story/Use Case как документация — см. ниже.]

1. Знакомство с системой
Story 1.1: Первый запуск бота
... (см. содержание, которое вы прислали)

2. Загрузка данных и запуск анализа
Story 2.1: Запуск нового анализа
... (см. содержание)

3. Мониторинг выполнения задач
...

4. Получение и работа с результатами
...

5. Управление задачами
...

6. Обработка ошибок
...

Use Case 1: Стандартный анализ одиночного образца
...

Use Case 2: Сравнительный анализ когорты пациентов
...

Use Case 3: Диагностика неудачного анализа
...
"""

import asyncio
import logging
import uuid
from io import BytesIO
from datetime import datetime, timezone

from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputFile
from aiogram import F

# Конфиг: поместите в config.py ваш TOKEN
from config import TOKEN

# --- Настройка логирования ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Простая модель задач в памяти (TaskManager) ---
class TaskStatus:
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"

class TaskManager:
    def __init__(self):
        # task_id -> metadata
        self.tasks = {}
        # task_id -> asyncio.Task (background)
        self._bg_tasks = {}

    def create_task(self, owner_id: str, filename: str, params: dict, file_path: str = None):
        task_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc)
        meta = {
            "id": task_id,
            "owner_id": owner_id,
            "filename": filename,
            "params": params,
            "status": TaskStatus.PENDING,
            "created_at": created_at,
            "started_at": None,
            "finished_at": None,
            "result": None,  # bytes or path for report
            "log": [],
            "file_path": file_path,
        }
        self.tasks[task_id] = meta
        return task_id

    def set_status(self, task_id, status):
        t = self.tasks.get(task_id)
        if not t:
            return
        t["status"] = status
        if status == TaskStatus.RUNNING:
            t["started_at"] = datetime.now(timezone.utc)
        if status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELED):
            t["finished_at"] = datetime.now(timezone.utc)

    def add_log(self, task_id, message):
        t = self.tasks.get(task_id)
        if t:
            t["log"].append(f"[{datetime.now(timezone.utc).isoformat()}] {message}")

    def attach_result(self, task_id, bytes_io: BytesIO, filename: str):
        t = self.tasks.get(task_id)
        if t:
            t["result"] = {"bytes": bytes_io.getvalue(), "filename": filename}

    def get(self, task_id):
        return self.tasks.get(task_id)

    def list_for_user(self, owner_id, filters=None):
        res = [t for t in self.tasks.values() if t["owner_id"] == owner_id]
        if not filters:
            return res
        # поддерживаем простые фильтры: instrument, reference, clustering, status
        for k, v in filters.items():
            res = [t for t in res if t["params"].get(k) == v or t.get(k) == v]
        return res

    def cancel_task(self, task_id):
        # попытка отменить bg asyncio.Task
        bg = self._bg_tasks.get(task_id)
        if bg and not bg.done():
            bg.cancel()
        self.set_status(task_id, TaskStatus.CANCELED)

    def store_bg_task(self, task_id, bg_task: asyncio.Task):
        self._bg_tasks[task_id] = bg_task

task_manager = TaskManager()

# --- FSM состояния для диалогов ---
class RunAnalysisStates(StatesGroup):
    waiting_fastq = State()
    waiting_tool = State()
    waiting_reference = State()
    waiting_clustering = State()
    confirm = State()

class CreateCohortStates(StatesGroup):
    waiting_task_list = State()
    waiting_metadata = State()
    confirm = State()

# --- Inline клавиатуры ---
def start_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Начать анализ", callback_data="start_analysis")],
        [InlineKeyboardButton(text="Помощь", callback_data="show_help")]
    ])
    return kb

def tool_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("QIIME2", callback_data="tool:QIIME2"),
         InlineKeyboardButton("DADA2", callback_data="tool:DADA2")],
        [InlineKeyboardButton("USEARCH", callback_data="tool:USEARCH")],
        [InlineKeyboardButton("Отменить", callback_data="run_cancel")]
    ])
    return kb

def reference_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("SILVA", callback_data="ref:SILVA"),
         InlineKeyboardButton("Greengenes", callback_data="ref:Greengenes")],
        [InlineKeyboardButton("Отменить", callback_data="run_cancel")]
    ])
    return kb

def clustering_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("OTU", callback_data="cluster:OTU"),
         InlineKeyboardButton("ASV", callback_data="cluster:ASV")],
        [InlineKeyboardButton("Отменить", callback_data="run_cancel")]
    ])
    return kb

# --- Фоновая "обработка" задачи: симуляция анализа и генерация PDF-отчёта ---
async def simulate_analysis_and_generate_report(task_id: str, bot: Bot):
    """
    Симулирует работу пайплайна: sleep -> генерирует PDF (reportlab) -> сохраняет результат в task_manager
    В реальном коде здесь будет запуск реальной обработки (QIIME2/DADA2 и пр), взаимодействие с очередями и т.д.
    """
    t = task_manager.get(task_id)
    if not t:
        return
    try:
        task_manager.set_status(task_id, TaskStatus.RUNNING)
        task_manager.add_log(task_id, "Запуск анализа (симуляция).")
        # ---- симуляция этапов с логированием ----
        await asyncio.sleep(1)  # загрузка
        task_manager.add_log(task_id, "Контроль качества: сбор метрик (симуляция).")
        await asyncio.sleep(1)
        task_manager.add_log(task_id, "Кластеризация/аннотация (симуляция).")
        await asyncio.sleep(1)

        # ---- генерация простого PDF отчёта ----
        pdf_bytes = BytesIO()
        filename = f"report_{task_id}.pdf"
        try:
            # reportlab используется для генерации PDF
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            c = canvas.Canvas(pdf_bytes, pagesize=letter)
            c.setFont("Helvetica", 12)
            c.drawString(72, 720, f"Task ID: {task_id}")
            c.drawString(72, 700, f"Sample file: {t['filename']}")
            c.drawString(72, 680, f"Instrument: {t['params'].get('instrument')}")
            c.drawString(72, 660, f"Reference: {t['params'].get('reference')}")
            c.drawString(72, 640, f"Clustering: {t['params'].get('clustering')}")
            c.drawString(72, 600, " --- Simulated QC plot (placeholder) ---")
            c.drawString(72, 580, "Alpha diversity: (simulated values)")
            c.drawString(72, 560, "Beta diversity: (simulated values)")
            c.drawString(72, 540, "Taxonomy table: (simulated)")
            c.showPage()
            c.save()
            pdf_bytes.seek(0)
        except Exception as e:
            # fallback: если нет reportlab, создаём простой текст-файл с расширением .pdf (не настоящий PDF)
            task_manager.add_log(task_id, f"reportlab not available or failed: {e}. Using TXT fallback.")
            pdf_bytes = BytesIO()
            txt = [
                f"Task ID: {task_id}",
                f"Sample file: {t['filename']}",
                f"Instrument: {t['params'].get('instrument')}",
                f"Reference: {t['params'].get('reference')}",
                f"Clustering: {t['params'].get('clustering')}",
                "",
                "Simulated report (reportlab not installed)."
            ]
            pdf_bytes.write("\n".join(txt).encode("utf-8"))
            pdf_bytes.seek(0)
            filename = f"report_{task_id}.txt"

        # attach result
        task_manager.attach_result(task_id, pdf_bytes, filename)
        task_manager.set_status(task_id, TaskStatus.COMPLETED)
        task_manager.add_log(task_id, "Анализ завершён успешно.")
        # уведомление пользователя (не блокирующее)
        try:
            owner = t["owner_id"]
            # отправим приватное уведомление пользователю, что задача завершена
            await bot.send_message(int(owner), f"Задача {task_id} завершена. Используйте /get_report {task_id} чтобы скачать отчёт.")
        except Exception:
            # возможно пользователь заблокировал бота или ошибка отправки — игнорируем
            logger.exception("Не удалось уведомить пользователя о завершении задачи.")
    except asyncio.CancelledError:
        task_manager.add_log(task_id, "Фоновая задача была отменена.")
        task_manager.set_status(task_id, TaskStatus.CANCELED)
    except Exception as e:
        logger.exception("Ошибка в simulate_analysis_and_generate_report")
        task_manager.add_log(task_id, f"Ошибка при обработке: {e}")
        task_manager.set_status(task_id, TaskStatus.FAILED)
        # уведомление пользователя об ошибке
        try:
            await bot.send_message(int(t["owner_id"]), f"Задача {task_id} завершилась с ошибкой. Используйте /status {task_id} для деталей.")
        except Exception:
            pass

# --- Хэндлеры команд и callback'ов ---
async def cmd_start(message: Message, state: FSMContext):
    tg_id = str(message.from_user.id)
    name = message.from_user.first_name or "пользователь"
    # Обновлённая входная строка (замена "Что я умею:" на запрошенную)
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

# --- Запуск диалога для /run_analysis ---
async def cmd_run_analysis(message: Message, state: FSMContext):
    await state.set_state(RunAnalysisStates.waiting_fastq)
    await message.answer(
        "Запуск нового анализа: загрузите FASTQ (или архив FASTQ) в виде файла (прикрепите документ).",
        reply_markup=types.ReplyKeyboardRemove()
    )

# Хэндлер получения документа FASTQ
async def handle_fastq_upload(message: Message, state: FSMContext):
    state_name = await state.get_state()
    if state_name != RunAnalysisStates.waiting_fastq.state:
        # если не ожидаем файл — игнорируем этот обработчик
        return
    if not message.document:
        await message.answer("Пожалуйста, пришлите файл как документ (не фото).")
        return
    doc = message.document
    # Скачивание файла на диск/временное хранилище
    try:
        # сохраняем временно в рабочую папку ./uploads/<tg_id>_<filename>
        owner = str(message.from_user.id)
        local_path = f"uploads/{owner}_{doc.file_name}"
        # message.document.download может быть coroutine or method in aiogram v3
        await message.document.download(destination_file=local_path)
    except Exception as e:
        logger.exception("Ошибка при сохранении файла")
        await message.answer("Не удалось сохранить файл. Попробуйте ещё раз.")
        return

    # Сохраняем путь и имя в FSM context
    await state.update_data(uploaded_file=local_path, filename=doc.file_name)
    # просим выбрать инструмент
    await state.set_state(RunAnalysisStates.waiting_tool)
    await message.answer("Файл принят. Выберите инструмент анализа:", reply_markup=tool_kb())

# Callback: выбор инструмента / reference / clustering
async def callback_tool_ref_cluster(cb: CallbackQuery, state: FSMContext):
    data = cb.data or ""
    if data.startswith("tool:"):
        tool = data.split(":", 1)[1]
        await state.update_data(instrument=tool)
        await state.set_state(RunAnalysisStates.waiting_reference)
        await cb.message.edit_text(f"Выбран инструмент: {tool}\nВыберите референсную базу:", reply_markup=reference_kb())
        await cb.answer()
    elif data.startswith("ref:"):
        ref = data.split(":", 1)[1]
        await state.update_data(reference=ref)
        await state.set_state(RunAnalysisStates.waiting_clustering)
        await cb.message.edit_text(f"Выбрана база: {ref}\nВыберите тип кластеризации:", reply_markup=clustering_kb())
        await cb.answer()
    elif data.startswith("cluster:"):
        cluster = data.split(":", 1)[1]
        await state.update_data(clustering=cluster)
        data_all = await state.get_data()
        # Подтверждение
        summary = (
            f"Параметры для запуска:\n"
            f"- Файл: {data_all.get('filename')}\n"
            f"- Инструмент: {data_all.get('instrument')}\n"
            f"- База: {data_all.get('reference')}\n"
            f"- Кластеризация: {data_all.get('clustering')}\n\n"
            "Подтвердите запуск анализа."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton("Запустить анализ", callback_data="confirm_run")],
            [InlineKeyboardButton("Отменить", callback_data="run_cancel")]
        ])
        await state.set_state(RunAnalysisStates.confirm)
        await cb.message.edit_text(summary, reply_markup=kb)
        await cb.answer()
    elif data == "run_cancel":
        await state.clear()
        await cb.message.edit_text("Запуск анализа отменён.")
        await cb.answer()

# Подтверждение запуска
async def callback_confirm_run(cb: CallbackQuery, bot: Bot, state: FSMContext):
    if cb.data != "confirm_run":
        return
    data_all = await state.get_data()
    owner = str(cb.from_user.id)
    filename = data_all.get("filename", "uploaded.fastq")
    params = {
        "instrument": data_all.get("instrument"),
        "reference": data_all.get("reference"),
        "clustering": data_all.get("clustering")
    }
    file_path = data_all.get("uploaded_file")  # путь к файлу в локальном хранилище
    task_id = task_manager.create_task(owner, filename, params, file_path=file_path)
    task_manager.add_log(task_id, "Задача создана пользователем.")
    await cb.message.edit_text(f"Задача создана. Task ID: {task_id}\nСтатус: pending. Вам придёт уведомление по завершению.")
    await cb.answer()

    # запускаем фоновую обработку
    bg = asyncio.create_task(simulate_analysis_and_generate_report(task_id, bot))
    task_manager.store_bg_task(task_id, bg)
    await state.clear()

# --- Команды для мониторинга и управления ---
async def cmd_status(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Использование: /status <task_id>")
        return
    task_id = args[1].strip()
    t = task_manager.get(task_id)
    if not t:
        await message.answer(f"Задача {task_id} не найдена.")
        return
    # Собираем информацию
    text = (
        f"Task ID: {t['id']}\n"
        f"Статус: {t['status']}\n"
        f"Файл: {t['filename']}\n"
        f"Параметры: instrument={t['params'].get('instrument')}, reference={t['params'].get('reference')}, clustering={t['params'].get('clustering')}\n"
        f"Создана: {t['created_at'].isoformat()}\n"
    )
    if t["started_at"]:
        text += f"Начата: {t['started_at'].isoformat()}\n"
    if t["finished_at"]:
        text += f"Завершена: {t['finished_at'].isoformat()}\n"
    # Добавим последние 10 логов
    logs = t.get("log", [])[-10:]
    if logs:
        text += "\nЛоги (последние):\n" + "\n".join(logs)
    await message.answer(text)

async def cmd_list_analyses(message: Message):
    # поддержка простого фильтра через аргументы: ключ=значение
    args = message.text.split(maxsplit=1)
    filters = {}
    if len(args) > 1:
        raw = args[1]
        for part in raw.split():
            if "=" in part:
                k, v = part.split("=", 1)
                filters[k] = v
    owner = str(message.from_user.id)
    tasks = task_manager.list_for_user(owner, filters=filters)
    if not tasks:
        await message.answer("У вас нет задач, соответствующих фильтру.")
        return
    lines = []
    for t in sorted(tasks, key=lambda x: x["created_at"], reverse=True)[:50]:
        lines.append(f"{t['id'][:8]}... | {t['filename']} | {t['params'].get('instrument')} | {t['status']}")
    await message.answer("Ваши задачи:\n" + "\n".join(lines))

async def cmd_get_report(message: Message, bot: Bot):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Использование: /get_report <task_id>")
        return
    task_id = args[1].strip()
    t = task_manager.get(task_id)
    if not t:
        await message.answer(f"Задача {task_id} не найдена.")
        return
    if t["status"] != TaskStatus.COMPLETED or not t.get("result"):
        await message.answer(f"Отчёт по задаче {task_id} ещё не готов. Текущий статус: {t['status']}")
        return
    result = t["result"]
    bio = BytesIO(result["bytes"])
    bio.seek(0)
    filename = result.get("filename", f"report_{task_id}.pdf")
    await bot.send_document(chat_id=message.chat.id, document=InputFile(bio, filename=filename))

async def cmd_cancel(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Использование: /cancel <task_id>")
        return
    task_id = args[1].strip()
    t = task_manager.get(task_id)
    if not t:
        await message.answer(f"Задача {task_id} не найдена.")
        return
    if t["status"] in (TaskStatus.PENDING, TaskStatus.RUNNING):
        task_manager.cancel_task(task_id)
        await message.answer(f"Задача {task_id} была отменена.")
    else:
        await message.answer(f"Задачу {task_id} нельзя отменить в статусе {t['status']}.")

# --- Создание когорты (/create_cohort) ---
async def cmd_create_cohort(message: Message, state: FSMContext):
    await message.answer(
        "Создание когорты: отправьте список task_id через запятую (минимум 10 задач), которые нужно объединить в когортный отчёт.\n"
        "Пример: taskid1,taskid2,taskid3,..."
    )
    await state.set_state(CreateCohortStates.waiting_task_list)

async def handle_cohort_task_list(message: Message, state: FSMContext, bot: Bot):
    if await state.get_state() != CreateCohortStates.waiting_task_list.state:
        return
    raw = message.text.strip()
    ids = [s.strip() for s in raw.split(",") if s.strip()]
    if len(ids) < 10:
        await message.answer("Нужно выбрать минимум 10 задач для когорты.")
        await state.clear()
        return
    # проверяем все задачи существуют и завершены
    tasks = []
    for tid in ids:
        t = task_manager.get(tid)
        if not t:
            await message.answer(f"Задача {tid} не найдена. Отмена создания когорты.")
            await state.clear()
            return
        if t["status"] != TaskStatus.COMPLETED:
            await message.answer(f"Задача {tid} не завершена (статус {t['status']}). Когорта требует завершённых задач. Отмена.")
            await state.clear()
            return
        tasks.append(t)
    # генерируем объединённый отчёт — простая сборка нескольких PDF-страниц
    combined = BytesIO()
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        c = canvas.Canvas(combined, pagesize=letter)
        for t in tasks:
            c.setFont("Helvetica", 12)
            c.drawString(72, 720, f"Cohort report - Task {t['id']}")
            c.drawString(72, 700, f"Sample file: {t['filename']}")
            c.drawString(72, 680, f"Params: {t['params']}")
            c.drawString(72, 640, "Aggregated metrics (simulated)")
            c.showPage()
        c.save()
        combined.seek(0)
        filename = f"cohort_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        await bot.send_document(chat_id=message.chat.id, document=InputFile(combined, filename=filename))
        await message.answer("Когортный отчёт создан и отправлен.")
    except Exception as e:
        logger.exception("Ошибка при создании когортного отчёта")
        await message.answer("Не удалось создать PDF-отчёт (не установлен reportlab).")
    await state.clear()

# Callback from стартовой клавиатуры
async def callback_start_buttons(cb: CallbackQuery):
    if cb.data == "start_analysis":
        # инициируем диалог как /run_analysis
        await cb.message.answer("Запустим диалог запуска анализа. Пожалуйста, используйте команду /run_analysis чтобы начать.")
        await cb.answer()
    elif cb.data == "show_help":
        await cb.message.answer("Вызов помощи: используйте команду /help")
        await cb.answer()

# --- Регистрация и запуск ---
async def main():
    bot = Bot(token=TOKEN)
    dp = Dispatcher()

    # регистрация команд
    dp.message.register(cmd_start, Command(commands=["start"]))
    dp.message.register(cmd_help, Command(commands=["help"]))
    dp.message.register(cmd_run_analysis, Command(commands=["run_analysis"]))
    dp.message.register(cmd_create_cohort, Command(commands=["create_cohort"]))
    dp.message.register(cmd_status, Command(commands=["status"]))
    dp.message.register(cmd_list_analyses, Command(commands=["list_analyses"]))
    dp.message.register(cmd_get_report, Command(commands=["get_report"]))
    dp.message.register(cmd_cancel, Command(commands=["cancel"]))

    # обработчик загрузки документа (FASTQ) — будет срабатывать когда FSM в соответствующем состоянии
    dp.message.register(handle_fastq_upload, F.document, RunAnalysisStates.waiting_fastq)

    # callback'и для выбора инструментов/подтверждений
    dp.callback_query.register(callback_tool_ref_cluster, F.data.startswith(("tool:", "ref:", "cluster:", "run_cancel")))
    dp.callback_query.register(callback_confirm_run, F.data == "confirm_run")

    # стартовые кнопки
    dp.callback_query.register(callback_start_buttons, F.data.in_(["start_analysis", "show_help"]))

    # обработчик ввода списка задач для когорты
    dp.message.register(handle_cohort_task_list, CreateCohortStates.waiting_task_list)

    # старт polling
    logger.info("Bot started")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")
