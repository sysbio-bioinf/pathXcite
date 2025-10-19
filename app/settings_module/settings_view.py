"""Main settings view for the application"""

# --- Standard Library Imports ---
import json
import os
import shutil

# --- Third Party Imports ---
from PyQt5.QtCore import QRegularExpression, Qt, QThread, QUrl
from PyQt5.QtGui import QDesktopServices, QRegularExpressionValidator
from PyQt5.QtSvg import QSvgWidget
from PyQt5.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

# --- Local Imports ---
from app.settings_module.api_settings.ping_worker import PingWorker
from app.settings_module.gene_set_library_settings.download_worker import DownloadWorker
from app.util_widgets.collapsible_widget import CollapsibleSection
from app.util_widgets.separator import get_separator

# --- Constants ---
EMAIL_RE = QRegularExpression(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

# --- Public Classes ---


class SettingsView(QWidget):
    """Main settings view for the application."""

    def __init__(self, parent=None, main_app=None, folder_path=None, assets_path=None, config=None):
        super().__init__(parent)

        self.assets_path = assets_path
        self.main_app = main_app
        self.folder_path = folder_path

        self.downloaded_set: set
        self.custom_entries: list[dict]
        self.progress_target: int
        self.progress_done: int
        self.ping_thread: QThread
        self.ping_worker: PingWorker

        self.library_list_file = f"{self.assets_path}/external_data/gmt_files_info.json"
        with open(self.library_list_file, "r", encoding="utf-8") as f:
            self.library_names = json.load(f)  # dict: {name: size}

        # Folder where .gmt files live
        self.gmt_folder = f"{self.assets_path}/external_data/gmt_files"
        os.makedirs(self.gmt_folder, exist_ok=True)

        self.custom_gmt_folder = f"{self.assets_path}/external_data/custom_gmt_files"
        os.makedirs(self.custom_gmt_folder, exist_ok=True)

        # Icon paths
        self.yes_svg_path = f"{self.assets_path}/icons/yes.svg"
        self.no_svg_path = f"{self.assets_path}/icons/no.svg"
        self.proc_svg_path = f"{self.assets_path}/icons/process.svg"

        if config is None:
            config = {
                "project_folder": folder_path,
                "api_email": None,
                "api_key": None
            }
        else:
            self.api_email = config.get("api_email", None)
            self.api_key = config.get("api_key", None)

        self.config = config

        self.setContentsMargins(0, 0, 0, 0)

        # Left stack (navigation)
        self.left_stack = QStackedWidget()
        self.left_stack.setFixedWidth(200)

        # Right area
        self.right_side = QWidget()
        self.right_side_layout = QVBoxLayout(self.right_side)

        self.right_stack = QStackedWidget()
        self.right_side_layout.addWidget(self.right_stack)

        # Bottom button bar
        self.button_bar = QWidget()
        self.button_bar_layout = QHBoxLayout(self.button_bar)

        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self._save_settings)

        self.button_bar_layout.addWidget(self.save_btn)

        self.right_side_layout.addWidget(self.button_bar)

        self.left_stack.setContentsMargins(0, 0, 0, 0)
        self.right_stack.setContentsMargins(0, 0, 0, 0)

        # Left navigation
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        account_api_btn = QPushButton("Account & API")
        libraries_btn = QPushButton("Gene Set Libraries")
        left_layout.addWidget(account_api_btn)
        left_layout.addWidget(libraries_btn)
        account_api_btn.clicked.connect(lambda: self._change_page(0))
        libraries_btn.clicked.connect(lambda: self._change_page(1))
        left_layout.addStretch()
        self.left_stack.addWidget(left_widget)

        # Build right pages
        self._init_api_settings()
        self._init_gene_set_libraries_settings()

        # Separator
        vline = get_separator("vertical")

        # Main layout
        layout = QHBoxLayout(self)
        layout.addWidget(self.left_stack)
        layout.addWidget(vline)
        layout.addWidget(self.right_side)
        self.setLayout(layout)

        self._apply_stylesheet()

        # Thread holder
        self._thread = None
        self._worker = None

        # Load initial values into the settings UI
        self._load_settings(source="init")

    # --- Private Methods ---
    def _apply_stylesheet(self) -> None:
        """Applies the stylesheet to the settings view."""
        stylesheet_path = f"{self.assets_path}/style/stylesheet.qss"
        try:
            with open(stylesheet_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        except Exception:
            pass

    def _change_page(self, index: int) -> None:
        """Changes the current page in the settings view.

        Args:
            index (int): The index of the page to switch to.
        """
        self.left_stack.setCurrentIndex(index)
        self.right_stack.setCurrentIndex(index)

        if index == 0:
            self.save_btn.setVisible(True)
        else:
            self.save_btn.setVisible(False)

    def _init_api_settings(self) -> None:
        """Initializes the API settings page."""
        api_settings_widget = QWidget()
        outer = QVBoxLayout(api_settings_widget)
        form = QFormLayout()
        outer.addLayout(form)

        # --- email ---
        email_input = QLineEdit()
        email_input.setObjectName("emailInput")
        email_input.setFixedWidth(300)
        email_input.setPlaceholderText("you@example.com")
        email_input.setClearButtonEnabled(True)
        email_input.setToolTip(
            "NCBI requires a valid email to contact you if needed.")
        email_re = QRegularExpression(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
        email_input.setValidator(QRegularExpressionValidator(email_re))

        # --- api key ---
        api_key_input = QLineEdit()
        api_key_input.setObjectName("apiKeyInput")
        api_key_input.setFixedWidth(300)
        api_key_input.setPlaceholderText(
            "NCBI API key (optional, speeds up requests)")
        api_key_input.setEchoMode(QLineEdit.Password)
        api_key_input.setClearButtonEnabled(True)
        api_key_input.setToolTip(
            "Paste your NCBI API key. This increases your E-utilities rate limits.")
        api_key_re = QRegularExpression(r"^\S{0,128}$")
        api_key_input.setValidator(QRegularExpressionValidator(api_key_re))

        # show/hide
        show_key_cb = QCheckBox("Show")
        show_key_cb.stateChanged.connect(
            lambda state: api_key_input.setEchoMode(
                QLineEdit.Normal if state == Qt.Checked else QLineEdit.Password)
        )

        key_row = QHBoxLayout()
        key_row.addWidget(api_key_input, 1)
        key_row.addWidget(show_key_cb, 0, Qt.AlignLeft)

        help_link = QLabel(
            '''<a href="https://www.ncbi.nlm.nih.gov/account/settings/">
                Get an API key (Will open an external browser)
            </a>
            '''
        )
        help_link.setOpenExternalLinks(True)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        test_btn = QPushButton("Test")
        clear_btn = QPushButton("Clear")
        btn_row.addWidget(test_btn)
        btn_row.addWidget(clear_btn)
        btn_row.addStretch()

        form.addRow(QLabel("<b>Entrez API Settings</b>"))
        form.addRow("Email:", email_input)
        form.addRow("API Key:", key_row)
        form.addRow("", help_link)
        outer.addLayout(btn_row)
        outer.addStretch()

        clear_btn.clicked.connect(
            lambda: (email_input.clear(), api_key_input.clear()))

        # Reuse the same validator the Save button will use
        test_btn.clicked.connect(lambda: self._validate_and_then_apply(
            email_input.text().strip(), api_key_input.text().strip(),
            on_success=lambda: QMessageBox.information(
                self, "Entrez Settings", "Ping OK ✅"),
            on_failure=lambda msg: QMessageBox.warning(
                self, "Entrez Settings", msg)
        ))

        self.right_stack.addWidget(api_settings_widget)

    def _init_gene_set_libraries_settings(self) -> None:
        """Initializes the Gene Set Libraries settings page."""
        self.gene_set_libraries_widget = QWidget()
        root = QVBoxLayout(self.gene_set_libraries_widget)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        # ---------- TOP: Gene Set Libraries (expanded initially) ----------
        top_section = CollapsibleSection(
            "Gene Set Libraries", start_collapsed=False, parent=self)
        # right side of header: downloaded count
        self.count_label = QLabel("")
        top_section.header_right_layout.addWidget(self.count_label)

        # Table
        self.library_table = QTableWidget()
        self.library_table.setColumnCount(4)
        self.library_table.setHorizontalHeaderLabels(
            ["Library", "Size", "File Size (KB)", "Downloaded"])
        self.library_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.library_table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.library_table.verticalHeader().setVisible(False)
        self.library_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.library_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeToContents)
        self.library_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeToContents)
        self.library_table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeToContents)

        # Populate
        self._refresh_downloaded_cache()
        libs_sorted = sorted(self.library_names.keys())
        self.library_table.setRowCount(len(libs_sorted))
        for row, lib in enumerate(libs_sorted):
            name_item = QTableWidgetItem(lib)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.library_table.setItem(row, 0, name_item)

            num_terms = self.library_names[lib].get("num_terms", 0)
            size_item = QTableWidgetItem(str(num_terms))
            size_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            size_item.setFlags(size_item.flags() & ~Qt.ItemIsEditable)
            self.library_table.setItem(row, 1, size_item)

            file_size = self.library_names[lib].get("file_size", 0)
            file_size_item = QTableWidgetItem(f"{file_size / 1024:.1f} KB")
            file_size_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            file_size_item.setFlags(
                file_size_item.flags() & ~Qt.ItemIsEditable)
            self.library_table.setItem(row, 2, file_size_item)

            icon_path = self.yes_svg_path if self._is_downloaded(
                lib) else self.no_svg_path
            self._set_icon_cell(row, icon_path)

        top_section.content_layout.addWidget(self.library_table)

        # Controls row with progress
        controls = QHBoxLayout()
        self.download_btn = QPushButton("Download Selected")
        controls.addWidget(self.download_btn)
        controls.addStretch()
        self.progress_label = QLabel("Total progress:")
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        controls.addWidget(self.progress_label)
        controls.addWidget(self.progress_bar)

        # add controls to top content
        top_controls_w = QWidget()
        top_controls_w.setLayout(controls)
        top_section.content_layout.addWidget(top_controls_w)

        # Wire button and initial counts
        self.download_btn.clicked.connect(self._on_download_selected)
        self._update_count_label()

        # ---------- BOTTOM: Custom Libraries (collapsed initially) ----------
        bottom_section = CollapsibleSection(
            "Custom Libraries", start_collapsed=True, parent=self)
        self.custom_count_label = QLabel("")
        bottom_section.header_right_layout.addWidget(self.custom_count_label)

        self.custom_table = QTableWidget()
        self.custom_table.setColumnCount(4)
        self.custom_table.setHorizontalHeaderLabels(
            ["File", "# Terms", "File Size (KB)", "Valid"])
        self.custom_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.custom_table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.custom_table.verticalHeader().setVisible(False)
        self.custom_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.custom_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeToContents)
        self.custom_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeToContents)
        self.custom_table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeToContents)

        bottom_section.content_layout.addWidget(self.custom_table)

        # Controls for custom libs
        c_controls = QHBoxLayout()
        self.add_custom_btn = QPushButton("Add .gmt")
        self.remove_custom_btn = QPushButton("Remove Selected")
        self.open_custom_folder_btn = QPushButton("Open Folder")
        c_controls.addWidget(self.add_custom_btn)
        c_controls.addWidget(self.remove_custom_btn)
        c_controls.addStretch()
        c_controls.addWidget(self.open_custom_folder_btn)
        c_controls_w = QWidget()
        c_controls_w.setLayout(c_controls)
        bottom_section.content_layout.addWidget(c_controls_w)

        # Wire custom actions
        self.add_custom_btn.clicked.connect(self._on_add_custom)
        self.remove_custom_btn.clicked.connect(self._on_remove_custom)
        self.open_custom_folder_btn.clicked.connect(
            self._on_open_custom_folder)

        # Populate custom table
        self._refresh_custom_cache()
        self._populate_custom_table()
        self._update_custom_count_label()

        # ---------- Assemble ----------
        root.addWidget(top_section)
        root.addWidget(get_separator("horizontal"))
        root.addWidget(bottom_section)
        root.addStretch()

        self.right_stack.addWidget(self.gene_set_libraries_widget)

    def _refresh_downloaded_cache(self) -> None:
        """Refreshes the cache of downloaded libraries."""
        self.downloaded_set = set()
        if os.path.isdir(self.gmt_folder):
            for root, _, files in os.walk(self.gmt_folder):
                for filename in files:
                    if filename.endswith(".gmt"):
                        full = os.path.join(root, filename)
                        if os.path.getsize(full) > 0:
                            self.downloaded_set.add(
                                os.path.splitext(filename)[0])

    def _is_downloaded(self, lib_name: str) -> bool:
        """Checks if a library is downloaded.

        Args:
            lib_name: Name of the library.
        """
        return lib_name in self.downloaded_set

    def _set_icon_cell(self, row: int, svg_path: str) -> None:
        """Sets the icon cell in the library table.

        Args:
            row: The row index.
            svg_path: The path to the SVG icon.
        """
        svg_widget = QSvgWidget(svg_path)
        svg_widget.setFixedSize(24, 24)
        cell_widget = QWidget()
        cell_layout = QHBoxLayout(cell_widget)
        cell_layout.addWidget(svg_widget)
        cell_layout.setAlignment(Qt.AlignCenter)
        cell_layout.setContentsMargins(0, 0, 0, 0)
        cell_widget.setLayout(cell_layout)
        self.library_table.setCellWidget(row, 3, cell_widget)

    def _update_count_label(self) -> None:
        """Updates the downloaded count label."""
        total = len(self.library_names)
        downloaded = len(self.downloaded_set)
        self.count_label.setText(f"Downloaded: {downloaded} / {total}")

    def _selected_rows_and_names(self) -> list[tuple[int, str]]:
        """Gets the selected rows and library names from the table.

        Returns:
            A list of tuples containing the row index and library name.
        """
        rows = sorted(
            {idx.row() for idx in self.library_table.selectionModel().selectedRows()})
        libs = []
        for r in rows:
            name = self.library_table.item(r, 0).text()
            libs.append((r, name))
        return libs

    def _on_download_selected(self) -> None:
        """Handles the download of selected libraries."""
        rows_and_names = self._selected_rows_and_names()
        if not rows_and_names:
            QMessageBox.information(
                self, "No Selection", "Please select one or more libraries in the table.")
            return

        # Determine which of the selections still need downloading
        self._refresh_downloaded_cache()
        to_download = [(r, n)
                       for (r, n) in rows_and_names if not self._is_downloaded(n)]

        if not to_download:
            QMessageBox.information(
                self, "All Present", "All selected libraries are already downloaded.")
            return

        # Confirmation with count
        count = len(to_download)
        total_size_in_bytes_of_to_downloaded = 0
        for _, name in to_download:
            total_size_in_bytes_of_to_downloaded += self.library_names.get(
                name, {}).get("file_size", 0)

        total_size_in_mb_of_to_downloaded = total_size_in_bytes_of_to_downloaded / \
            (1024 * 1024)
        reply = QMessageBox.question(
            self,
            "Confirm Download",
            f"You selected {len(rows_and_names)} libraries.\n"
            f"{count} not yet downloaded will be fetched.\n"
            f"Total size: {total_size_in_mb_of_to_downloaded:.2f} MB\n\nProceed?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        # Prepare UI for run
        self.download_btn.setEnabled(False)
        # Mark rows as "in progress"
        for r, _name in to_download:
            self._set_icon_cell(r, self.proc_svg_path)

        # Progress bar init (fills per completed download)
        self.progress_bar.setValue(0)
        self.progress_target = count
        self.progress_done = 0
        if count > 0:
            self.progress_bar.setMaximum(count)
            self.progress_bar.setFormat("%v / %m")

        # Start worker thread
        self._thread = QThread(self)
        self._worker = DownloadWorker(to_download, self.gmt_folder)
        self._worker.moveToThread(self._thread)

        # show progress bar and label
        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)

        self._thread.started.connect(self._worker.run)
        self._worker.started_library.connect(self._on_started_library)
        self._worker.finished_library.connect(self._on_finished_library)
        self._worker.all_done.connect(self._on_all_done)

        # Clean up
        self._worker.all_done.connect(self._thread.quit)
        self._worker.all_done.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def _on_started_library(self, row: int, lib_name: str) -> None:
        """Handles the start of a library download."""
        self._set_icon_cell(row, self.proc_svg_path)

    def _on_finished_library(self, row: int, lib_name: str, success: bool) -> None:
        """Handles the completion of a library download."""
        # Refresh cache for accurate state
        if success:
            self.downloaded_set.add(lib_name)
            self._set_icon_cell(row, self.yes_svg_path)
        else:
            # Revert to 'no' if failed
            self._set_icon_cell(row, self.no_svg_path)

        # advance total progress on each finished
        self.progress_done += 1
        self.progress_bar.setValue(self.progress_done)

        # Update header count only when success changes installed set
        if success:
            self._update_count_label()

            # notify main app of new libraries
            self.main_app.update_gmt_libraries(sorted(self.downloaded_set))

    def _on_all_done(self) -> None:
        """Handles the completion of all downloads."""
        # Ensure label is correct
        self._refresh_downloaded_cache()
        self._update_count_label()
        # Restore button
        self.download_btn.setEnabled(True)

        # hide progress bar and label
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)

    def _load_settings(self, source=None) -> None:
        """Loads settings into the UI."""
        email_input = self.findChild(QLineEdit, "emailInput")
        api_key_input = self.findChild(QLineEdit, "apiKeyInput")

        email = (self.config or {}).get("api_email") or ""
        key = (self.config or {}).get("api_key") or ""

        if not email:
            return  # nothing to validate; leave blanks

        # Disable while checking
        for w in (email_input, api_key_input):
            if w:
                w.setEnabled(False)

        def on_success() -> None:
            """Handles successful validation of saved credentials."""
            if email_input:
                email_input.setText(email)
            if api_key_input:
                api_key_input.setText(key)
            if source is None:
                self.main_app.update_config(
                    {"api_email": email, "api_key": key})
            for w in (email_input, api_key_input):
                if w:
                    w.setEnabled(True)

        def on_failure(msg: str):
            if email_input:
                email_input.clear()
            if api_key_input:
                api_key_input.clear()
            for w in (email_input, api_key_input):
                if w:
                    w.setEnabled(True)
            # QMessageBox.warning(self, "Entrez",
            # f"Saved credentials could not be verified.\n{msg}")

        self._validate_and_then_apply(email, key, on_success, on_failure)

    def _save_settings(self) -> None:
        """Saves the settings from the UI."""
        email_input = self.findChild(QLineEdit, "emailInput")
        api_key_input = self.findChild(QLineEdit, "apiKeyInput")
        save_btn = self.save_btn

        pending_email = (email_input.text() if email_input else "").strip()
        pending_key = (api_key_input.text() if api_key_input else "").strip()

        if not _is_valid_email(pending_email):
            QMessageBox.warning(self, "Settings not saved",
                                "Please enter a valid email address.")
            return

        save_btn.setEnabled(False)

        def on_success():
            self.config["api_email"] = pending_email
            self.config["api_key"] = pending_key
            self.main_app.update_config(self.config)
            QMessageBox.information(self, "Settings", "Saved successfully.")
            save_btn.setEnabled(True)

        def on_failure(msg: str):
            QMessageBox.warning(self, "Settings not saved", msg)
            save_btn.setEnabled(True)

        self._validate_and_then_apply(
            pending_email, pending_key, on_success, on_failure)

    def _validate_and_then_apply(self, email: str, api_key: str, on_success, on_failure) -> None:
        """Validates the email and API key by pinging NCBI.

        Args:
            email: The email address to validate.
            api_key: The API key to validate.
            on_success: Callback on success.
            on_failure: Callback on failure with error message.
        """

        # validate the value, not the widget content
        if not _is_valid_email(email):
            on_failure("Please enter a valid email address.")
            return

        # Fresh ping thread/worker to not reuse old state
        if hasattr(self, "ping_thread") and self.ping_thread is not None:
            try:
                self.ping_thread.quit()
                self.ping_thread.wait(100)
            except Exception:
                pass

        self.ping_thread = QThread(self)
        self.ping_worker = PingWorker(email, api_key, tool_name="pathXcite")
        self.ping_worker.moveToThread(self.ping_thread)

        self.ping_thread.started.connect(self.ping_worker.run)
        self.ping_worker.finished.connect(self.ping_thread.quit)
        self.ping_thread.finished.connect(self.ping_worker.deleteLater)
        self.ping_thread.finished.connect(self.ping_thread.deleteLater)

        def _finish(ok: bool, msg: str):
            if ok:
                on_success()
            else:
                on_failure(msg)

        self.ping_worker.finished.connect(_finish)
        self.ping_thread.start()

    def _validate_gmt_and_count(self, file_path: str) -> tuple[bool, int, str]:
        """
        Validates a GMT file and counts the number of terms.
        Returns:
            (is_valid, num_terms, error_msg).

        """
        num_terms = 0
        try:
            with open(file_path, "r", encoding="utf-8") as fh:
                for ln, line in enumerate(fh, 1):
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split("\t")
                    if len(parts) < 3:
                        return (False, num_terms, f"Line {ln}: fewer than 3 tab-separated fields")
                    # basic gene presence check
                    genes = [g for g in parts[2:] if g]
                    if len(genes) == 0:
                        return (False, num_terms, f"Line {ln}: no genes provided")
                    num_terms += 1
            if num_terms == 0:
                return (False, 0, "No terms found")
            return (True, num_terms, "")
        except Exception as e:
            return (False, 0, f"Error reading file: {e}")

    def _refresh_custom_cache(self):
        self.custom_entries: list[dict] = []  # list of dicts
        if not os.path.isdir(self.custom_gmt_folder):
            return
        for fn in sorted(os.listdir(self.custom_gmt_folder)):
            if not fn.lower().endswith(".gmt"):
                continue
            full = os.path.join(self.custom_gmt_folder, fn)
            size = os.path.getsize(full)
            is_valid, n_terms, _err = self._validate_gmt_and_count(full)
            self.custom_entries.append({
                "file": fn,
                "path": full,
                "size_kb": size / 1024.0,
                "valid": is_valid,
                "num_terms": n_terms
            })

    def _populate_custom_table(self) -> None:
        """Populates the custom libraries table."""
        self.custom_table.setRowCount(len(self.custom_entries))
        for row, ent in enumerate(self.custom_entries):
            # File
            it0 = QTableWidgetItem(ent["file"])
            it0.setFlags(it0.flags() & ~Qt.ItemIsEditable)
            self.custom_table.setItem(row, 0, it0)

            # # Terms
            it1 = QTableWidgetItem(str(ent["num_terms"]))
            it1.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            it1.setFlags(it1.flags() & ~Qt.ItemIsEditable)
            self.custom_table.setItem(row, 1, it1)

            # Size
            it2 = QTableWidgetItem(f"{ent['size_kb']:.1f} KB")
            it2.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            it2.setFlags(it2.flags() & ~Qt.ItemIsEditable)
            self.custom_table.setItem(row, 2, it2)

            # Valid icon
            svg = self.yes_svg_path if ent["valid"] else self.no_svg_path
            w = QWidget()
            lay = QHBoxLayout(w)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.setAlignment(Qt.AlignCenter)
            svgw = QSvgWidget(svg)
            svgw.setFixedSize(24, 24)
            lay.addWidget(svgw)
            w.setLayout(lay)
            self.custom_table.setCellWidget(row, 3, w)

    def _update_custom_count_label(self) -> None:
        """Updates the custom libraries count label."""
        total = len(self.custom_entries)
        valid = sum(1 for e in self.custom_entries if e["valid"])
        self.custom_count_label.setText(f"Valid: {valid} / {total}")

    def _on_add_custom(self) -> None:
        """Handles adding custom GMT files."""
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select .gmt file(s) to add",
            "",
            "GMT files (*.gmt);;All files (*)"
        )
        if not paths:
            return

        added = 0
        skipped = 0
        invalids = []
        for src in paths:
            if not src.lower().endswith(".gmt"):
                skipped += 1
                continue

            ok, n_terms, err = self._validate_gmt_and_count(src)
            if not ok:
                invalids.append((os.path.basename(src), err))
                continue

            dst = os.path.join(self.custom_gmt_folder, os.path.basename(src))
            if os.path.exists(dst):
                reply = QMessageBox.question(
                    self, "Overwrite?",
                    f"'{os.path.basename(src)}' already exists in custom_gmt_files.\nOverwrite?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if reply != QMessageBox.Yes:
                    skipped += 1
                    continue

            try:
                shutil.copy2(src, dst)
                added += 1
            except Exception as e:
                invalids.append((os.path.basename(src), f"Copy failed: {e}"))

        # refresh UI
        self._refresh_custom_cache()
        self._populate_custom_table()
        self._update_custom_count_label()

        # notify main app
        try:
            if hasattr(self.main_app, "update_custom_gmt_libraries"):
                self.main_app.update_custom_gmt_libraries(
                    [e["path"] for e in self.custom_entries if e["valid"]]
                )
        except Exception:
            pass

        # feedback
        msg = [f"Added: {added}"]
        if skipped:
            msg.append(f"Skipped: {skipped}")
        if invalids:
            msg.append(f"Invalid/failed: {len(invalids)}")
        QMessageBox.information(self, "Custom Libraries", "\n".join(msg))

        if invalids:
            details = "\n".join(
                [f"- {name}: {reason}" for name, reason in invalids])
            QMessageBox.warning(self, "Some files were invalid", details)

    def _on_remove_custom(self) -> None:
        """Handles removing selected custom GMT files."""
        sel_rows = sorted({idx.row() for idx in self.custom_table.selectionModel(
        ).selectedRows()}, reverse=True)
        if not sel_rows:
            QMessageBox.information(
                self, "Remove", "Select one or more custom libraries to remove.")
            return

        names = [self.custom_table.item(r, 0).text() for r in sel_rows]
        reply = QMessageBox.question(
            self, "Confirm Removal",
            "Remove the following files from custom_gmt_files?\n\n" +
            "\n".join(names),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        removed = 0
        errs = []
        for r in sel_rows:
            fn = self.custom_table.item(r, 0).text()
            path = os.path.join(self.custom_gmt_folder, fn)
            try:
                if os.path.exists(path):
                    os.remove(path)
                    removed += 1
            except Exception as e:
                errs.append((fn, str(e)))

        self._refresh_custom_cache()
        self._populate_custom_table()
        self._update_custom_count_label()

        try:
            if hasattr(self.main_app, "update_custom_gmt_libraries"):
                self.main_app.update_custom_gmt_libraries(
                    [e["path"] for e in self.custom_entries if e["valid"]]
                )
        except Exception:
            pass

        msg = [f"Removed: {removed}"]
        if errs:
            msg.append(f"Failed: {len(errs)}")
        QMessageBox.information(self, "Custom Libraries", "\n".join(msg))
        if errs:
            details = "\n".join(
                [f"- {name}: {reason}" for name, reason in errs])
            QMessageBox.warning(
                self, "Some files couldn't be removed", details)

    def _on_open_custom_folder(self) -> None:
        """Handles opening the custom GMT folder."""
        path = self.custom_gmt_folder
        if not os.path.isdir(path):
            QMessageBox.warning(self, "Open Folder",
                                f"Folder does not exist:\n{path}")
            return

        # Primary, cross-platform way via Qt
        if QDesktopServices.openUrl(QUrl.fromLocalFile(path)):
            return

        # Fallback per-OS (rarely needed)
        try:
            import platform
            import subprocess
            system = platform.system().lower()
            if "darwin" in system:
                subprocess.check_call(["open", path])
            elif "windows" in system:
                subprocess.check_call(["explorer", path])
            else:  # linux / other unix
                subprocess.check_call(["xdg-open", path])
        except Exception as e:
            QMessageBox.warning(self, "Open Folder",
                                f"Could not open folder:\n{e}")


# --- Private Functions ---
def _is_valid_email(s: str) -> bool:
    """Validates an email address format."""
    return bool(s) and EMAIL_RE.match(s).hasMatch()
