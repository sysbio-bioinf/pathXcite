"""Top bar widget with toolbars and database selection"""

# --- Standard Library Imports ---
import os
from pathlib import Path

# --- Third Party Imports ---
from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

# --- Local Imports ---
from app.util_widgets.icon_button import SvgIconButton


# --- Public Classes ---
class TopBar(QWidget):
    """Top bar widget with toolbars and database selection."""

    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app
        self.db_name_to_path = {}

        # === Top-level layout (vertical to allow two rows) ===
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # === First row: Panel with toolbar1 and DB controls ===
        panel = QWidget()
        panel_layout = QHBoxLayout()
        panel_layout.setContentsMargins(5, 0, 5, 0)

        self.toolbar = QToolBar()
        self.toolbar.setMovable(False)
        self.toolbar.setFloatable(False)
        self.toolbar.setIconSize(QSize(24, 24))
        self.toolbar.setStyleSheet(
            "QToolBar { background: transparent; border: none; }")
        self.toolbar.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        panel_layout.addWidget(self.toolbar)

        # === DB label + dropdown + add button ===
        db_label = QLabel("Current Database:")
        db_label.setStyleSheet(
            "color: white; font-size: 12px; margin-right: 5px;")

        self.db_dropdown = QComboBox()
        self.db_dropdown.setStyleSheet("""
            QComboBox {
                background-color: white;
                padding: 2px;
                min-width: 150px;
            }
        """)

        self.add_new_db_button = SvgIconButton(
            svg_inactive="new_db_inactive2.svg",
            svg_hover="new_db_hover2.svg",
            svg_active="new_db_active2.svg",
            icon_size=QSize(24, 24),
            parent=self,
            main_app=self.main_app,
            callback=self.main_app.add_new_database
        )

        panel_layout.addStretch(1)
        panel_layout.addWidget(db_label)
        panel_layout.addWidget(self.db_dropdown)
        panel_layout.addWidget(self.add_new_db_button)

        panel.setLayout(panel_layout)
        main_layout.addWidget(panel)

        panel2 = QWidget()
        panel2_layout = QHBoxLayout()
        panel2_layout.setContentsMargins(5, 0, 5, 0)

        # === Second row: Toolbar2 ===
        self.toolbar2 = QToolBar()
        self.toolbar2.setMovable(False)
        self.toolbar2.setFloatable(False)
        self.toolbar2.setIconSize(QSize(24, 24))
        self.toolbar2.setStyleSheet(
            "QToolBar { background: transparent; border: none; }")
        self.toolbar2.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        self.toolbar2.setVisible(False)  # Hidden by default
        panel2_layout.addWidget(self.toolbar2)
        panel2_layout.addStretch(1)
        panel2.setLayout(panel2_layout)
        main_layout.addWidget(panel2)

        self.setLayout(main_layout)
        self.setFixedHeight(50)  # Height to accommodate two toolbars if needed
        self.db_dropdown.currentIndexChanged.connect(self._on_database_changed)

    # --- Public Functions ---

    def set_toolbar_actions(self, actions) -> None:
        """Set actions for toolbar1."""
        self.toolbar.clear()
        if actions:
            self.toolbar.addActions(actions)

    def set_toolbar2_actions(self, actions) -> None:
        """Set actions for toolbar2."""
        self.toolbar2.clear()
        if actions:
            self.toolbar2.addActions(actions)
            self.toolbar2.setVisible(True)

    def toggle_toolbar2(self, visible: bool = None) -> None:
        """Toggle toolbar2 visibility. If 'visible' is None, it toggles current state."""
        if visible is None:
            visible = not self.toolbar2.isVisible()
        self.toolbar2.setVisible(visible)
        if visible:
            self.setFixedHeight(80)
        else:
            self.setFixedHeight(40)

    def set_database_list(self, db_list: list[str]) -> None:
        """Set the list of databases in the dropdown.

        Args:
            db_list (list[str]): List of database file paths.
        """
        self.db_name_to_path.clear()
        self.db_dropdown.clear()
        for db_path in db_list:
            if db_path.endswith(".db"):
                db_name = Path(db_path).name
                self.db_name_to_path[db_name] = db_path
                self.db_dropdown.addItem(db_name)

    def get_current_db_ids(self) -> list[str]:
        """Get the IDs of the current database.
         Returns:
            list[str]: List of database IDs in lowercase.
        """
        saved_ids = self.main_app.get_db_ids()
        return [id.lower() for id in saved_ids.get("pmids", []) + saved_ids.get("pmcids", [])]

    def get_current_database(self) -> str:
        """Get the file path of the currently selected database.

        Returns:
            str: File path of the selected database.
        """
        name = self.db_dropdown.currentText()
        return self.db_name_to_path.get(name, "")

    def update_dropdown(self, valid_databases, selection_preference=None) -> None:
        """Update the database dropdown with valid databases.

        Args:
            valid_databases (dict): Mapping of database file paths to number of articles.
            selection_preference (str, optional): Preferred database name to select. 
            Defaults to None.
        """
        self.db_dropdown.blockSignals(True)
        self.db_name_to_path.clear()
        self.db_dropdown.clear()

        for db_path, _ in valid_databases.items():
            db_name = os.path.basename(db_path)
            self.db_name_to_path[db_name] = db_path
            self.db_dropdown.addItem(db_name)

        if selection_preference and selection_preference in self.db_name_to_path:
            index = self.db_dropdown.findText(selection_preference)
            if index != -1:
                self.db_dropdown.setCurrentIndex(index)

        self.db_dropdown.blockSignals(False)
        self.main_app.change_triggered()

    def update_current_database(self, db_name: str) -> None:
        """Update the currently selected database in the dropdown.

        Args:
            db_name (str): Name of the database to select.
        """
        db_name = os.path.basename(db_name)
        if db_name not in self.db_name_to_path:
            return
        index = self.db_dropdown.findText(db_name)
        if index == -1:
            return
        self.db_dropdown.blockSignals(True)
        self.db_dropdown.setCurrentIndex(index)
        self.db_dropdown.blockSignals(False)

    # --- Private Functions ---
    def _on_database_changed(self, index) -> None:
        """Handle database change event.

        Args:
            index (int): Index of the newly selected database.
        """
        self.main_app.change_triggered()

    '''def replace_toolbar(self, new_widget):
        toolbar_layout = QHBoxLayout(self.toolbar_widget)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        toolbar_layout.setSpacing(5)
        self.toolbar_widget.setFixedWidth(400)

        # Clear existing toolbar buttons
        for i in reversed(range(toolbar_layout.count())):
            widget = toolbar_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        # Add new widget to the toolbar
        toolbar_layout.addWidget(new_widget)'''
