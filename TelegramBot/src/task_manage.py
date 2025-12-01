import asyncio
import uuid
from datetime import datetime, timezone
from io import BytesIO
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


@dataclass
class TaskResult:
    bytes: bytes
    filename: str


@dataclass
class TaskMetadata:
    id: str
    owner_id: str
    filename: str
    params: Dict[str, Any]
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    result: Optional[TaskResult] = None
    log: List[str] = field(default_factory=list)
    file_path: Optional[str] = None


class TaskManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TaskManager, cls).__new__(cls)
            cls._instance.tasks: Dict[str, TaskMetadata] = {}
            cls._instance._bg_tasks: Dict[str, asyncio.Task] = {}
        return cls._instance

    def create_task(self, owner_id: str, filename: str, params: dict, file_path: str = None) -> str:
        task_id = str(uuid.uuid4())
        meta = TaskMetadata(
            id=task_id,
            owner_id=owner_id,
            filename=filename,
            params=params,
            file_path=file_path
        )
        self.tasks[task_id] = meta
        return task_id

    def get(self, task_id: str) -> Optional[TaskMetadata]:
        return self.tasks.get(task_id)

    def set_status(self, task_id: str, status: TaskStatus):
        t = self.tasks.get(task_id)
        if not t:
            return
        t.status = status
        if status == TaskStatus.RUNNING:
            t.started_at = datetime.now(timezone.utc)
        elif status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELED):
            t.finished_at = datetime.now(timezone.utc)

    def add_log(self, task_id: str, message: str):
        t = self.tasks.get(task_id)
        if t:
            t.log.append(f"[{datetime.now(timezone.utc).isoformat()}] {message}")

    def attach_result(self, task_id: str, bytes_io: BytesIO, filename: str):
        t = self.tasks.get(task_id)
        if t:
            t.result = TaskResult(bytes=bytes_io.getvalue(), filename=filename)

    def list_for_user(self, owner_id: str, filters: Optional[Dict] = None) -> List[TaskMetadata]:
        res = [t for t in self.tasks.values() if t.owner_id == owner_id]
        if not filters:
            return res
        for k, v in filters.items():
            res = [t for t in res if t.params.get(k) == v]
        return res

    def cancel_task(self, task_id: str):
        bg = self._bg_tasks.get(task_id)
        if bg and not bg.done():
            bg.cancel()
        self.set_status(task_id, TaskStatus.CANCELED)

    def store_bg_task(self, task_id: str, bg_task: asyncio.Task):
        self._bg_tasks[task_id] = bg_task