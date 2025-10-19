"""
Initial page widget for selecting project folder and creating 
database before opening the main app
"""

# --- Standard Library Imports ---
import json
import os

# --- Third Party Imports ---
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

# --- Local Imports ---
from app.database.database_creation import create_database
from app.database.database_validation import scan_and_validate_databases
from app.utils import resource_path


# -- Public Classes ---
class InitialPage(QWidget):
    """Initial page for selecting project folder and creating database if needed."""
    # Emit the chosen folder when ready to open
    open_requested = pyqtSignal(str)

    def __init__(self, parent=None, exit_on_open=False):
        super().__init__(parent)
        self.exit_on_open = exit_on_open

        self.stacked = QStackedWidget(self)
        self.stacked.setContentsMargins(0, 0, 0, 0)

        # --- STATE ---
        self.ready_to_open = False  # set True after a successful check
        self.db_creation_needed = False  # set True if the first DB is needed
        self.folder_path = ""  # selected project folder

        # --- PAGE 1: Welcome/Folder picker ---
        self.welcome_page = QWidget()
        welcome_layout = QVBoxLayout(self.welcome_page)
        welcome_layout.setSpacing(12)

        title = QLabel("<h2>Welcome to pathXcite</h2>")
        subtitle = QLabel("Select a project folder to get started.")
        subtitle.setWordWrap(True)

        file_row = QHBoxLayout()
        self.folder_edit = QLineEdit()
        self.folder_edit.setPlaceholderText("Project folder path")
        self.folder_edit.textChanged.connect(self._on_folder_text_changed)
        browse_btn = QPushButton("Choose Folder")
        browse_btn.clicked.connect(self._choose_folder)
        file_row.addWidget(self.folder_edit)
        file_row.addWidget(browse_btn)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.close_btn = QPushButton("Close")
        self.next_btn = QPushButton("Next")
        self.close_btn.clicked.connect(QApplication.instance().quit)
        self.next_btn.clicked.connect(self._on_next_clicked)
        self.next_btn.setEnabled(False)
        btn_row.addWidget(self.close_btn)
        btn_row.addWidget(self.next_btn)

        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet("color: #666;")
        self.status_lbl.setWordWrap(True)

        welcome_layout.addWidget(title)
        welcome_layout.addWidget(subtitle)
        welcome_layout.addLayout(file_row)
        welcome_layout.addWidget(self.status_lbl)
        welcome_layout.addStretch(1)
        welcome_layout.addLayout(btn_row)

        self.stacked.addWidget(self.welcome_page)

        # --- PAGE 2: DB name chooser (shown only if needed) ---
        self.db_page = QWidget()
        db_layout = QVBoxLayout(self.db_page)
        db_layout.setSpacing(12)

        db_title = QLabel("<h3>Create first database</h3>")
        db_title.setTextFormat(Qt.RichText)
        db_msg = QLabel(
            "No database found. Choose a name for your first database file.")
        db_msg.setWordWrap(True)

        db_row = QHBoxLayout()
        self.db_name_edit = QLineEdit()
        self.db_name_edit.setPlaceholderText("e.g. project.db")
        self.db_browse_btn = QPushButton("Browse…")
        self.db_browse_btn.clicked.connect(self._choose_db_filename)
        db_row.addWidget(self.db_name_edit)
        db_row.addWidget(self.db_browse_btn)

        back_next_row = QHBoxLayout()
        back_next_row.addStretch(1)
        self.back_btn = QPushButton("Back")
        self.back_btn.clicked.connect(self._back_to_welcome)
        self.open_btn = QPushButton("Open in pathXcite")
        self.open_btn.clicked.connect(self._on_open_clicked_from_db_page)
        back_next_row.addWidget(self.back_btn)
        back_next_row.addWidget(self.open_btn)

        db_layout.addWidget(db_title)
        db_layout.addWidget(db_msg)
        db_layout.addLayout(db_row)
        db_layout.addStretch(1)
        db_layout.addLayout(back_next_row)

        self.stacked.addWidget(self.db_page)

        # Root layout
        root = QVBoxLayout(self)
        root.addWidget(self.stacked)

        self._apply_stylesheet()

    # ------- UI actions -------
    def _choose_folder(self) -> None:
        """Open folder dialog to select project folder."""
        folder = QFileDialog.getExistingDirectory(
            self, "Select Project Folder")
        if folder:
            self.folder_edit.setText(folder)

    def _choose_db_filename(self) -> None:
        """Open file dialog to select database file."""
        base_dir = self.folder_path or os.getcwd()
        path, _ = QFileDialog.getSaveFileName(
            self, "Choose Database File", os.path.join(
                base_dir, "project.db"), "SQLite DB (*.db)"
        )
        if path:
            if not path.lower().endswith(".db"):
                path += ".db"
            self.db_name_edit.setText(path)

    def _back_to_welcome(self) -> None:
        """Switch back to the welcome page."""
        self.stacked.setCurrentWidget(self.welcome_page)
        self.db_creation_needed = False
        self.status_lbl.setText("")
        self.next_btn.setText("Next")
        self.ready_to_open = False

    def _on_folder_text_changed(self, text: str) -> None:
        """Update internal folder path and enable/disable Next button."""
        self.folder_path = text.strip()
        self.next_btn.setEnabled(bool(self.folder_path))

    # ------- Logic -------
    def _on_next_clicked(self) -> None:
        """
        First click: validate contents of the selected folder.
        If a .db exists, switch the primary button to 'Open in bio tool'.
        Otherwise, go to the DB-name page.
        If already ready_to_open, this acts as the final 'Open in bio tool' click.
        """
        if self.ready_to_open and self.stacked.currentWidget() is self.welcome_page:
            self._open_and_exit()
            return

        folder = self.folder_path
        if not folder or not os.path.isdir(folder):
            QMessageBox.warning(self, "Invalid folder",
                                "Please choose an existing folder.")
            return

        has_db = self._folder_has_db(folder)
        validation_results = scan_and_validate_databases(folder)
        number_valid_databases = 0
        for _, res in validation_results.items():
            if res.get("is_valid", False) is True:
                number_valid_databases += 1

        has_db = number_valid_databases > 0

        if has_db:
            if number_valid_databases == 1:
                self.status_lbl.setText(
                    "1 valid database found. You can open the project.")
            else:
                self.status_lbl.setText(
                    f"{number_valid_databases} valid databases found. You can open the project.")
            self.next_btn.setText("Open in PathXCite")
            self.ready_to_open = True
            self.db_creation_needed = False
        else:
            self.db_creation_needed = True
            suggested = os.path.join(folder, "project.db")
            self.db_name_edit.setText(suggested)
            self.stacked.setCurrentWidget(self.db_page)

    def _on_open_clicked_from_db_page(self) -> None:
        """
        From the DB-name page:
        create the DB, then proceed to open (which will silently ensure config.json).
        """
        if not self.db_creation_needed:
            self._open_and_exit()
            return

        folder = self.folder_path
        db_path = self.db_name_edit.text().strip()

        if not db_path:
            QMessageBox.warning(self, "Missing name",
                                "Please choose a database file name.")
            return

        if not os.path.isabs(db_path):
            db_path = os.path.join(folder, db_path)

        if not db_path.lower().endswith(".db"):
            db_path += ".db"

        parent = os.path.dirname(db_path) or folder
        if not os.path.isdir(parent):
            try:
                os.makedirs(parent, exist_ok=True)
            except Exception as e:
                QMessageBox.critical(
                    self, "Error", f"Cannot create directory:\n{e}")
                return

        try:
            create_database(db_path)
        except Exception as e:
            QMessageBox.critical(self, "Error creating database", str(e))
            return

        self._open_and_exit()

    def _open_and_exit(self) -> None:
        """Ensure config.json exists, then emit folder path and optionally quit."""
        try:
            config_path = os.path.join(self.folder_path, "config.json")
            if not os.path.isfile(config_path):
                config_data = {
                    "project_folder": self.folder_path,
                    "api_email": None,
                    "api_key": None
                }
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(config_data, f, ensure_ascii=False, indent=4)
        except Exception:
            pass  # silent best-effort

        # Emit the selected folder to the launcher
        self.open_requested.emit(self.folder_path)

        # Close this window. Only quit the whole app if explicitly requested.
        self.close()
        if self.exit_on_open:
            QApplication.instance().quit()

    @staticmethod
    def _folder_has_db(folder):
        try:
            for name in os.listdir(folder):
                if name.lower().endswith(".db") and os.path.isfile(os.path.join(folder, name)):
                    return True
        except Exception:
            pass
        return False

        ##### ============ STYLESHEET ============ #####

    def _apply_stylesheet(self) -> None:
        """Load and apply the stylesheet."""
        stylesheet_path = resource_path("assets/style/stylesheet.qss")
        if not stylesheet_path.exists():
            print(f"ERROR: The file does NOT exist at {stylesheet_path}")
            return
        try:
            with open(stylesheet_path, "r", encoding="utf-8") as f:
                stylesheet = f.read()
            self.setStyleSheet(stylesheet)
            if self.styleSheet() == "":
                print("ERROR: Stylesheet was NOT applied! Check for syntax errors.")
        except Exception as e:
            print(f"ERROR: Could not open stylesheet: {e}")
