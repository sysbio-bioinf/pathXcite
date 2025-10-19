"""Bottom information panel with stacked tabs for logs, task board, and project files"""

# --- Third Party Imports ---
from PyQt5.QtWidgets import QStackedWidget, QVBoxLayout, QWidget

# --- Local Imports ---
from app.info_panel.logs_tab import LogsTab
from app.info_panel.project_tab import ProjectFolderView
from app.utils import resource_path


# --- Public Classes ---
class InfoPanel(QWidget):
    '''LOGS_INDEX = 0
    TASK_BOARD_INDEX = 1
    PROJECT_FILES_INDEX = 2'''

    def __init__(self, folder_path, main_app, task_board, process_manager=None):
        """Info panel with stacked pages: Logs, Task Board, Project Files, Help."""
        super().__init__()
        self.main_app = main_app
        self.process_manager = process_manager
        self.task_board = task_board
        self.folder_path: str = folder_path

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self.stack = QStackedWidget()

        application_log_path = f"{folder_path}/application.log"
        self.logs_tab = LogsTab(application_log_path)
        self.project_tab = ProjectFolderView(folder_path, main_app)

        self.stack.addWidget(self.logs_tab)  # 0
        self.stack.addWidget(self.task_board)  # 1
        self.stack.addWidget(self.project_tab)  # 2

        layout.addWidget(self.stack)
        self.setLayout(layout)

    # --- Public Methods ---
    def add_log(self, text: str, mode: str = "INFO") -> None:
        """Adds a log entry to the logs page.

        Args:
            text: Log message text.
            mode: Log level (e.g., "INFO", "ERROR").
        """
        self.logs_tab.add_log(text, level=mode)

    def show_tab(self, index: int) -> None:
        """Shows the specified page by index (kept name for API compatibility).

        Args:
            index: Index of the tab to show.
        """
        self.stack.setCurrentIndex(index)

    # --- Private Methods ---
    def _set_folder_path(self, folder_path: str) -> None:
        """Updates the folder path in the project page.

        Args:
            folder_path: New folder path to set.
        """
        self.folder_path = folder_path
        self.project_tab.set_folder_path(folder_path)
