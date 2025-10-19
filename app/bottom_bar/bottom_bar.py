"""Bottom bar widget for the main application window."""

# --- Standard Library Imports ---
from typing import Any

# --- Third Party Imports ---
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtWidgets import QHBoxLayout, QSizePolicy, QWidget

# --- Local Imports ---
from app.util_widgets.svg_button import SvgHoverButton

# --- Public Classes ---


class BottomBar(QWidget):
    """
    Bottom bar widget containing buttons for expanding/collapsing info box and opening various tabs.

    Args:
        main_app: Main application instance for interaction.
    """

    def __init__(self, main_app: Any):
        super().__init__()
        self.main_app = main_app
        self.db_name_to_path: dict[str, str] = {}

        # Create main layout
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Create a panel widget to hold the labels and set its background
        panel = QWidget()
        panel.setStyleSheet("background-color: #cccccc;")

        # Create a layout for the panel
        panel_layout = QHBoxLayout()
        panel_layout.setContentsMargins(0, 0, 0, 0)

        # Create buttons
        self.expand_button = SvgHoverButton(
            base_name="up",
            tooltip="Expand Info Box",
            triggered_func=lambda: self._expand_info_box(),
            size=20
        )

        self.collapse_button = SvgHoverButton(
            base_name="down",
            tooltip="Collapse Info Box",
            triggered_func=lambda: self._collapse_info_box(),
            size=20
        )
        self.collapse_button.setVisible(False)

        self.open_project_folder_button = SvgHoverButton(
            base_name="folder",
            tooltip="Open Project Folder",
            triggered_func=lambda: self._open_project_folder_tab(),
            size=20
        )

        self.open_log_button = SvgHoverButton(
            base_name="log",
            tooltip="Open Log",
            triggered_func=lambda: self._open_log_tab(),
            size=20
        )

        self.open_processes_button = SvgHoverButton(
            base_name="processes",
            tooltip="Open Processes",
            triggered_func=lambda: self._open_processes_tab(),
            size=20
        )

        # Add buttons to the panel layout
        panel_layout.addWidget(self.expand_button)
        panel_layout.addWidget(self.collapse_button)
        panel_layout.addWidget(self.open_project_folder_button)
        panel_layout.addWidget(self.open_log_button)
        panel_layout.addWidget(self.open_processes_button)
        panel_layout.addStretch(1)

        buttons = [self.expand_button,
                   self.collapse_button,
                   self.open_project_folder_button,
                   self.open_log_button,
                   self.open_processes_button]

        for widget in buttons:
            panel_layout.setAlignment(widget, Qt.AlignVCenter)

        panel_layout.setSpacing(0)

        for button in buttons:
            button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            button.setFixedSize(22, 22)
            button.setIconSize(QSize(20, 20))

        panel.setLayout(panel_layout)
        main_layout.addWidget(panel)

        self.setLayout(main_layout)
        self.setFixedHeight(24)

    # --- Private Methods ---

    def _open_project_folder_tab(self) -> None:
        """Open the project folder tab in the logs panel."""
        self.main_app.logs_panel.show_tab(2)
        self._expand_info_box()

    def _open_log_tab(self) -> None:
        """Open the log tab in the logs panel."""
        self.main_app.logs_panel.show_tab(0)
        self._expand_info_box()

    def _open_processes_tab(self) -> None:
        """Open the processes tab in the logs panel."""
        self.main_app.logs_panel.show_tab(1)
        self._expand_info_box()

    def _collapse_info_box(self) -> None:
        """Collapse the info box."""
        self.main_app.collapse_log_panel()
        self.expand_button.setVisible(True)
        self.collapse_button.setVisible(False)

    def _expand_info_box(self) -> None:
        """Expand the info box."""
        self.main_app.expand_log_panel()
        self.expand_button.setVisible(False)
        self.collapse_button.setVisible(True)
