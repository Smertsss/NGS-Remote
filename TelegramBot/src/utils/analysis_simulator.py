import asyncio
import logging
from io import BytesIO
from ..task_manage import TaskManager, TaskStatus

logger = logging.getLogger(__name__)


async def simulate_analysis_and_generate_report(task_id: str, bot, dp):
    """
    Симулирует работу пайплайна и генерирует PDF-отчёт
    Добавлен параметр dp (dispatcher) для корректного завершения
    """
    task_manager = TaskManager()
    t = task_manager.get(task_id)
    if not t:
        return

    try:
        task_manager.set_status(task_id, TaskStatus.RUNNING)
        task_manager.add_log(task_id, "Запуск анализа (симуляция).")

        # ---- симуляция этапов с логированием ----
        await asyncio.sleep(1)
        task_manager.add_log(task_id, "Контроль качества: сбор метрик (симуляция).")
        await asyncio.sleep(1)
        task_manager.add_log(task_id, "Кластеризация/аннотация (симуляция).")
        await asyncio.sleep(1)

        # ---- генерация простого PDF отчёта ----
        pdf_bytes = BytesIO()
        filename = f"report_{task_id}.pdf"

        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            c = canvas.Canvas(pdf_bytes, pagesize=letter)
            c.setFont("Helvetica", 12)
            c.drawString(72, 720, f"Task ID: {task_id}")
            c.drawString(72, 700, f"Sample file: {t.filename}")
            c.drawString(72, 680, f"Instrument: {t.params.get('instrument')}")
            c.drawString(72, 660, f"Reference: {t.params.get('reference')}")
            c.drawString(72, 640, f"Clustering: {t.params.get('clustering')}")
            c.drawString(72, 600, " --- Simulated QC plot (placeholder) ---")
            c.drawString(72, 580, "Alpha diversity: (simulated values)")
            c.drawString(72, 560, "Beta diversity: (simulated values)")
            c.drawString(72, 540, "Taxonomy table: (simulated)")
            c.showPage()
            c.save()
            pdf_bytes.seek(0)
        except Exception as e:
            task_manager.add_log(task_id, f"reportlab not available or failed: {e}. Using TXT fallback.")
            pdf_bytes = BytesIO()
            txt = [
                f"Task ID: {task_id}",
                f"Sample file: {t.filename}",
                f"Instrument: {t.params.get('instrument')}",
                f"Reference: {t.params.get('reference')}",
                f"Clustering: {t.params.get('clustering')}",
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

        # уведомление пользователя
        try:
            await bot.send_message(
                int(t.owner_id),
                f"Задача {task_id} завершена. Используйте /get_report {task_id} чтобы скачать отчёт."
            )
        except Exception:
            logger.exception("Не удалось уведомить пользователя о завершении задачи.")

    except asyncio.CancelledError:
        task_manager.add_log(task_id, "Фоновая задача была отменена.")
        task_manager.set_status(task_id, TaskStatus.CANCELED)
        logger.info(f"Задача {task_id} была корректно отменена")
    except Exception as e:
        logger.exception(f"Ошибка в simulate_analysis_and_generate_report для задачи {task_id}")
        task_manager.add_log(task_id, f"Ошибка при обработке: {e}")
        task_manager.set_status(task_id, TaskStatus.FAILED)
        try:
            await bot.send_message(
                int(t.owner_id),
                f"Задача {task_id} завершилась с ошибкой. Используйте /status {task_id} для деталей."
            )
        except Exception:
            pass