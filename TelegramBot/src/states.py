from aiogram.fsm.state import State, StatesGroup

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