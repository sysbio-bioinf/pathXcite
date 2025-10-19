"""Tab for displaying logs with timestamps and log levels"""

# --- Standard Library Imports ---
import os

# --- Third Party Imports ---
from PyQt5.QtCore import Q_ARG, QDateTime, QMetaObject, Qt, pyqtSlot
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import QTextEdit


# --- Public Classes ---
class LogsTab(QTextEdit):
    """ A tab for displaying logs with timestamps, log levels, and optional file saving. """

    LOG_LEVELS = {
        "INFO": ("INFO", "#00AA00"),       # Green
        "WARNING": ("WARNING", "#FFA500"),  # Orange
        "ERROR": ("ERROR", "#FF0000"),     # Red
        "DEBUG": ("DEBUG", "#0000FF"),     # Blue
    }

    def __init__(self, log_file: str = None):
        """Initializes the log tab."""
        super().__init__()
        self.setReadOnly(True)
        # self.setStyleSheet("font-family: Consolas; font-size: 12px;")
        self.log_file = log_file

        if self.log_file and not os.path.exists(self.log_file):
            with open(self.log_file, "w", encoding='utf-8') as f:
                f.write("==== Log Start ====\n")

    # --- Public Methods ---
    def add_log(self, message: str, level: str = "INFO") -> None:
        """
        Adds a log entry with a timestamp and log level.

        Args:
          message: The log message
         level: Log level (INFO, WARNING, ERROR, DEBUG)
        """
        timestamp = QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss")
        level_text, color = self.LOG_LEVELS.get(
            level, ("INFO", "#000000"))  # Default to INFO (black)

        log_entry = f"[{timestamp}] [{level_text}] {message}"
        colored_entry = f'<span style="color:{color};">{log_entry}</span>'

        # Append to UI in a thread-safe manner
        QMetaObject.invokeMethod(
            self, "_append_html", Qt.QueuedConnection, Q_ARG(str, colored_entry))

        # Save to log file if enabled
        if self.log_file:
            with open(self.log_file, "a", encoding='utf-8') as f:
                f.write(log_entry + "\n")

    # --- Private Slots ---
    @pyqtSlot(str)
    def _append_html(self, html_text):
        """ Safely appends colored HTML text to the log area. """
        self.append(html_text)
        self.moveCursor(QTextCursor.End)  # Auto-scroll
