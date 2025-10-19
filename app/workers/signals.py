"""Defines common worker signals for threading"""

from PyQt5.QtCore import QObject, pyqtSignal


class WorkerSignals(QObject):
    """Defines the signals available from a running worker thread."""
    finished = pyqtSignal(
        str, object)  # (task_id, payload) — payload can be results_df or None
    error = pyqtSignal(str, str)  # (task_id, message)
    progress = pyqtSignal(str, int)  # (task_id, percent)
    ui_update = pyqtSignal(str, object)  # (task_id, payload)
