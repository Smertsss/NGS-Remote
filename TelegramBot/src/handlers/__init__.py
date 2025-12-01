from .base import register_base_handlers
from .analysis import register_analysis_handlers
from .cohort import register_cohort_handlers
from .monitoring import register_monitoring_handlers
from .reports import register_report_handlers

def register_all_handlers(dp):
    """Регистрирует все хэндлеры"""
    register_base_handlers(dp)
    register_analysis_handlers(dp)
    register_cohort_handlers(dp)
    register_monitoring_handlers(dp)
    register_report_handlers(dp)