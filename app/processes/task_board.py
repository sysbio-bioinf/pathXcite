"""Task board widget displaying current background tasks with progress and controls"""

# --- Third Party Imports ---

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

# -- Local Imports ---
from app.processes.process_manager import ProcessManager, Task, TaskStatus
from app.util_widgets.svg_button import SvgHoverButton


# -- Public Classes ---
class TaskItemWidget(QFrame):
    """Widget representing a single task item with progress and controls."""

    def __init__(self, task: Task, on_cancel=None, on_pause=None, on_resume=None, on_remove=None):
        """Widget representing a single task item with progress and controls."""
        super().__init__()
        self.task_id = task.id
        self.on_cancel = on_cancel
        self.on_pause = on_pause
        self.on_resume = on_resume
        self.on_remove = on_remove

        # Frame + sizing
        self.setFrameShape(QFrame.StyledPanel)
        self.setObjectName("TaskItem")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Header
        title = QLabel(f"{task.name}  ({task.id})")
        title.setObjectName("TaskTitle")

        self.status_label = QLabel(task.status.value)
        self.status_label.setObjectName("StatusPill")
        self.status_label.setAlignment(Qt.AlignCenter)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(8)
        top.addWidget(title, 1)
        top.addWidget(self.status_label, 0, Qt.AlignRight)

        # Progress
        self.progress = QProgressBar()
        self.progress.setTextVisible(True)
        self.progress.setFixedHeight(14)

        if task.determinate:
            self.progress.setRange(0, 100)
            self.progress.setValue(task.progress)
        else:
            self.progress.setRange(0, 0)  # indeterminate

        # Controls (compact tool buttons with icons)
        style = self.style()

        self.btn_pause = QToolButton()
        self.btn_pause.setIcon(style.standardIcon(QStyle.SP_MediaPause))
        self.btn_pause.setToolTip("Pause")
        self.btn_pause.clicked.connect(
            lambda: self.on_pause and self.on_pause(self.task_id))

        self.btn_resume = QToolButton()
        self.btn_resume.setIcon(style.standardIcon(QStyle.SP_MediaPlay))
        self.btn_resume.setToolTip("Resume")
        self.btn_resume.clicked.connect(
            lambda: self.on_resume and self.on_resume(self.task_id))
        self.btn_resume.hide()

        self.btn_cancel = QToolButton()
        self.btn_cancel.setIcon(
            style.standardIcon(QStyle.SP_DialogCancelButton))
        self.btn_cancel.setToolTip("Cancel")
        self.btn_cancel.clicked.connect(
            lambda: self.on_cancel and self.on_cancel(self.task_id))

        self.btn_remove = SvgHoverButton("trash", tooltip="Remove",
                                         triggered_func=lambda: self.on_remove and self.on_remove(
                                             self.task_id),
                                         size=22, parent=self)
        self.btn_remove.hide()

        controls = QHBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(4)
        controls.addWidget(self.btn_pause)
        controls.addWidget(self.btn_resume)
        controls.addWidget(self.btn_cancel)
        controls.addWidget(self.btn_remove)

        bottom = QHBoxLayout()
        bottom.setContentsMargins(0, 0, 0, 0)
        bottom.setSpacing(8)
        bottom.addWidget(self.progress, 1)
        bottom.addLayout(controls, 0)

        # Root layout
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(6)
        lay.addLayout(top)
        lay.addLayout(bottom)

        self.refresh(task)

    # --- Public Methods ---
    def refresh(self, task: Task):
        """Refreshes the task item display based on the current task state."""
        self.status_label.setText(task.status.value)

        if task.determinate:
            if self.progress.minimum() == 0 and self.progress.maximum() == 0:
                self.progress.setRange(0, 100)
            self.progress.setValue(task.progress)
        else:
            self.progress.setRange(0, 0)

        terminal = task.status in (
            TaskStatus.DONE, TaskStatus.ERROR, TaskStatus.CANCELED)
        if terminal:
            if self.progress.minimum() == 0 and self.progress.maximum() == 0:
                self.progress.setRange(0, 100)
            self.progress.setValue(100)

            self.btn_pause.hide()
            self.btn_resume.hide()
            self.btn_cancel.hide()
            self.btn_remove.show()
        else:
            self.btn_remove.hide()
            if task.status == TaskStatus.PAUSED:
                self.btn_pause.hide()
                self.btn_resume.show()
            else:
                self.btn_pause.show()
                self.btn_resume.hide()


class TaskBoardWidget(QWidget):
    """Widget for displaying and managing the task board."""

    def __init__(self, process_manager: ProcessManager, on_cancel=None,
                 on_pause=None, on_resume=None):
        super().__init__()
        self.pm = process_manager
        self.on_cancel = on_cancel
        self.on_pause = on_pause
        self.on_resume = on_resume
        self._rows = {}

        # Scroll + container
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        self.container = QWidget()
        self.vbox = QVBoxLayout(self.container)
        self.vbox.setContentsMargins(0, 0, 0, 0)
        self.vbox.setSpacing(6)
        self.vbox.setAlignment(Qt.AlignTop)
        scroll.setWidget(self.container)

        # Header
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)

        title = QLabel("Tasks")
        title.setObjectName("HeaderTitle")

        self.count_label = QLabel("0")
        self.count_label.setObjectName("CountBadge")
        self.count_label.setAlignment(Qt.AlignCenter)

        clear_btn = QPushButton("Clear finished")
        clear_btn.setObjectName("ClearButton")
        clear_btn.clicked.connect(self._clear_finished)
        self.clear_btn = clear_btn

        header.addWidget(title)
        header.addWidget(self.count_label, 0, Qt.AlignLeft)
        header.addStretch()
        header.addWidget(clear_btn, 0, Qt.AlignRight)

        # Empty state
        self.empty_label = QLabel("No tasks yet")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setObjectName("EmptyState")
        self.empty_label.setVisible(False)

        # Root
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)
        root.addLayout(header)
        root.addWidget(scroll)
        root.addWidget(self.empty_label)

        # Light styling (scoped to this widget)
        self.setStyleSheet("""
        /* Header */
        QLabel#HeaderTitle { font-weight: 600; }
        QLabel#CountBadge {
            padding: 1px 6px;
            border-radius: 8px;
            background: rgba(0,0,0,0.06);
            font-size: 11px;
        }
        QPushButton#ClearButton { padding: 4px 8px; }
        QLabel#EmptyState { color: #777; font-style: italic; padding: 24px 0; }

        /* Task item */
        QFrame#TaskItem {
            border: 1px solid rgba(0,0,0,0.08);
            border-radius: 6px;
            background: rgba(0,0,0,0.02);
        }
        QLabel#TaskTitle { font-weight: 600; }
        QLabel#StatusPill {
            padding: 1px 8px;
            border-radius: 10px;
            background: rgba(0,0,0,0.08);
            font-size: 11px;
        }
        QProgressBar {
            border: 1px solid rgba(0,0,0,0.10);
            border-radius: 4px;
            text-align: center;
            font-size: 10px;
        }
        QProgressBar::chunk { border-radius: 3px; }
        """)

        # Signals
        self.pm.task_added.connect(self._add_row)
        self.pm.task_updated.connect(self._update_row)
        self.pm.task_removed.connect(self._remove_row)

        # Seed with existing
        for t in self.pm.tasks():
            self._add_row(t)

        self._update_header_state()

    # --- Private Methods ---
    def _update_row(self, task: Task):
        """Updates the display of a task item."""
        row = self._rows.get(task.id)
        if row:
            row.refresh(task)
        self._update_header_state()

    def _remove_row(self, task_id: str):
        """Removes a task item from the display."""
        row = self._rows.pop(task_id, None)
        if row:
            row.setParent(None)
            row.deleteLater()
        self._update_header_state()

    def _add_row(self, task: Task):
        """Adds a new task item to the display."""
        row = TaskItemWidget(
            task,
            self.on_cancel, self.on_pause, self.on_resume,
            on_remove=self._remove_via_pm
        )
        self.vbox.addWidget(row)
        self._rows[task.id] = row
        self._update_header_state()

    def _remove_via_pm(self, task_id: str):
        """Removes a task via the ProcessManager."""
        # calls ProcessManager so signals propagate correctly
        self.pm.remove_task(task_id)

    def _clear_finished(self):
        """Clears all finished tasks from the display."""
        finished_ids = [
            t.id for t in self.pm.tasks()
            if t.status in (TaskStatus.DONE, TaskStatus.ERROR, TaskStatus.CANCELED)
        ]
        for tid in finished_ids:
            self.pm.remove_task(tid)
        self._update_header_state()

    def _update_header_state(self):
        """Updates the header state (count, empty state, clear button)."""
        total = len(self._rows)
        self.count_label.setText(str(total))
        self.empty_label.setVisible(total == 0)

        # enable Clear when there's at least one terminal task
        any_terminal = False
        for t in self.pm.tasks():
            if t.status in (TaskStatus.DONE, TaskStatus.ERROR, TaskStatus.CANCELED):
                any_terminal = True
                break
        self.clear_btn.setEnabled(any_terminal)
