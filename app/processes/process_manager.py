"""Manages background tasks with progress and status updates"""

# -- Standard Library Imports ---
import itertools
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Optional

# -- Third Party Imports ---
from PyQt5.QtCore import QObject, pyqtSignal


# -- Public Classes ---
class TaskStatus(str, Enum):
    """Enumeration of possible task statuses."""
    PENDING = "Pending"
    RUNNING = "Running"
    PAUSED = "Paused"
    DONE = "Done"
    ERROR = "Error"
    CANCELED = "Canceled"


@dataclass
class Task:
    """Represents a background task with progress and status."""
    id: str
    name: str
    determinate: bool = True
    progress: int = 0                      # 0..100 (ignored if indeterminate)
    status: TaskStatus = TaskStatus.PENDING
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    extra: dict = field(default_factory=dict)


class ProcessManager(QObject):
    """Manages background tasks and emits signals on updates."""
    task_added = pyqtSignal(Task)
    task_updated = pyqtSignal(Task)
    task_removed = pyqtSignal(str)

    _id_counter = itertools.count(1)

    def __init__(self):
        super().__init__()
        self._tasks: Dict[str, Task] = {}

    # -- Public Methods --

    def add_indeterminate_task(self, name: str) -> str:
        """Adds an indeterminate background task."""
        return self._add_task(name, determinate=False)

    def add_task(self, name: str) -> str:
        """Adds a determinate background task."""
        return self._add_task(name, determinate=True)

    def update_task_progress(self, task_id: str, percent: int):
        """Updates the progress of a task."""
        t = self._tasks.get(task_id)
        if not t:
            return
        if t.determinate:
            t.progress = max(0, min(100, percent))
        t.status = TaskStatus.RUNNING
        self.task_updated.emit(t)

    def set_task_status(self, task_id: str, status: TaskStatus, *, error_msg: str = ""):
        """Sets the status of a task."""
        t = self._tasks.get(task_id)
        if not t:
            return
        t.status = status
        if status in (TaskStatus.DONE, TaskStatus.ERROR, TaskStatus.CANCELED):
            t.finished_at = datetime.now()
            if error_msg:
                t.extra["error"] = error_msg
        self.task_updated.emit(t)

    def stop_task(self, task_id: str):
        """Marks a task as done."""
        # convenience for DONE
        self.set_task_status(task_id, TaskStatus.DONE)

    def remove_task(self, task_id: str):
        """Removes a task from the manager."""
        if task_id in self._tasks:
            del self._tasks[task_id]
            self.task_removed.emit(task_id)

    def get(self, task_id: str) -> Optional[Task]:
        """Retrieves a task by its ID."""
        return self._tasks.get(task_id)

    def tasks(self):
        """Returns a list of all tasks."""
        return list(self._tasks.values())

    # -- Private Methods --
    def _add_task(self, name: str, determinate: bool) -> str:
        """Internal method to add a task."""
        task_id = f"T{next(self._id_counter)}"
        t = Task(id=task_id, name=name, determinate=determinate,
                 status=TaskStatus.RUNNING, started_at=datetime.now())
        self._tasks[task_id] = t
        self.task_added.emit(t)
        return task_id
