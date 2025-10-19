"""Provides the UI elements for the comparison settings module"""

# --- Standard Library Imports ---
import os
import re
from typing import Any

# --- Third Party Imports ---
from PyQt5.QtCore import QObject, Qt
from PyQt5.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QWidget,
    QWidgetAction,
)

# --- Local Imports ---
from app.util_widgets.clickable_widget import ClickableContainer
from app.util_widgets.droppable_line_edit import PathDropLineEdit
from app.util_widgets.svg_button import SvgHoverButton

# --- Public Classes ---


class ComparisonModuleView(QObject):
    """
    Provides all widgets and behavior for the 'comparison settings' UI,
    without placing anything in a layout.

    Exposes:
      - Labels: header_label, file1_text, file2_text, label1_text, label2_text, library_text
      - Editors: file1_input, file2_input, file1_label, file2_label, library_input
      - Buttons: file1_browse_btn, file2_browse_btn, submit_btn

    Args:
        main_app: Main application instance for interaction.
        parent: Parent widget for proper ownership.
    """

    def __init__(self, main_app: Any = None, parent: Any = None) -> None:
        super().__init__(parent)
        self.main_app = main_app

        self.toolbar_actions: list[QWidgetAction] = []
        self.toolbar_actions2: list[QWidgetAction] = []

        self.header_label = QLabel("Select two enrichment result files")
        self.header_label.setWordWrap(True)
        self.header_label.setTextFormat(Qt.PlainText)

        self.file1_text = QLabel("First file (.tsv):")
        self.file2_text = QLabel("Second file (.tsv):")
        self.file1_text.setFixedWidth(100)
        self.file2_text.setFixedWidth(100)

        self.library_text = QLabel("Library:")
        self.library_text.setFixedWidth(100)

        # ---- Inputs
        self.file1_input = PathDropLineEdit()
        self.file2_input = PathDropLineEdit()
        for le in (self.file1_input, self.file2_input):
            le.setPlaceholderText("Path to .tsv")
            le.setMinimumWidth(200)

        self.file1_label = QLineEdit()
        self.file2_label = QLineEdit()
        self.file1_label.setPlaceholderText(
            "Auto from first filename (editable)")
        self.file2_label.setPlaceholderText(
            "Auto from second filename (editable)")
        self.file1_label.setClearButtonEnabled(True)
        self.file2_label.setClearButtonEnabled(True)

        self.library_input = QLineEdit()
        self.library_input.setMinimumWidth(200)
        self.library_input.setPlaceholderText(
            "Gene set library (e.g., MSigDB hallmark)")
        self.library_input.setClearButtonEnabled(True)

        # ---- Buttons
        self.file1_browse_btn = SvgHoverButton(
            base_name="folder",
            tooltip="Browse for .tsv file",
            triggered_func=lambda: self._open_file_dialog(self.file1_input),
            size=20,
            parent=parent
        )

        self.file2_browse_btn = SvgHoverButton(
            base_name="folder",
            tooltip="Browse for .tsv file",
            triggered_func=lambda: self._open_file_dialog(self.file2_input),
            size=20,
            parent=parent
        )

        self.submit_btn = SvgHoverButton(
            base_name="compare3",
            tooltip="Load Comparison View",
            triggered_func=lambda: self._on_submit(),
            size=22,
            parent=parent
        )

        self.submit_button_widget = ClickableContainer()
        self.submit_button_widget.setObjectName("submitComposite")

        # layout "padding"
        self.submit_button_layout = QHBoxLayout(self.submit_button_widget)
        self.submit_button_layout.setContentsMargins(10, 0, 10, 0)
        self.submit_button_widget.setFixedHeight(30)
        self.submit_button_layout.setSpacing(8)

        # Make children transparent so the parent's bg shows through
        # If self.submit_btn is a QPushButton used as an icon, make it flat/transparent
        try:
            self.submit_btn.setFlat(True)
        except AttributeError:
            pass
        self.submit_btn.setStyleSheet("background: transparent; border: none;")
        # Labels are transparent by default

        # Style: use dynamic properties for hover/pressed
        self.submit_button_widget.setStyleSheet("""
            #submitComposite {
                background: #0F739E;
                color: #FFFFFF;
                border: 1px solid #0F739E;
                border-radius: 3px;
                font-weight: 600;
                /* padding is handled by layout margins */
            }
            /* hover state (use dynamic property to ensure it works over children) */
            #submitComposite[hover="true"] {
                background: #0F8088;
                border-color: #0F8088;
            }
            /* pressed state via dynamic property */
            #submitComposite[pressed="true"] {
                background: #0E5B52;
                border-color: #0E5B52;
            }
            /* disabled works with QWidget too */
            #submitComposite:disabled {
                background: #E1E6EA;
                border-color: #E1E6EA;
                color: #6A7A89;
            }
            """)

        self.submit_button_layout.addWidget(self.submit_btn)
        submit_label = QLabel("Create Comparison")
        submit_label.setStyleSheet(
            "background-color: transparent; color: white; font-weight: 600; border: none;")
        self.submit_button_layout.addWidget(submit_label)
        self.submit_button_widget.clicked.connect(self._on_submit)

        self.file1_input.editingFinished.connect(
            lambda: self._maybe_autofill_label(
                self.file1_input, self.file1_label)
        )
        self.file2_input.editingFinished.connect(
            lambda: self._maybe_autofill_label(
                self.file2_input, self.file2_label)
        )

        self.export_html_btn = SvgHoverButton(
            base_name="export",              # match the icon above
            tooltip="Export Comparison Results to HTML",
            triggered_func=lambda: self._on_export_html(),
            size=20,
            parent=parent
        )

        self._init_toolbar_actions()

    # --- Public Methods ---
    def get_comparison_inputs(self) -> dict[str, str]:
        """Retrieve current comparison input values.

        Args:
            None

        Returns:
            dict[str, str]: Dictionary with keys: file1, file2, label1, label2, library
        """
        return {
            "file1": self.file1_input.text().strip(),
            "file2": self.file2_input.text().strip(),
            "label1": self.file1_label.text().strip(),
            "label2": self.file2_label.text().strip(),
            "library": self.library_input.text().strip()
        }

    # --- Private Methods ---
    def _open_file_dialog(self, target_edit: QLineEdit) -> None:
        """
        Open a file dialog to select a .tsv file and set it in the target_edit.

        Args:
            target_edit: QLineEdit to set the selected file path into.
        Returns:
            None
        """
        start_dir = os.path.dirname(
            target_edit.text()) if target_edit.text() else os.getcwd()
        path, _ = QFileDialog.getOpenFileName(
            None,
            "Choose enrichment results file",
            start_dir,
            "TSV Files (*.tsv);;All Files (*)"
        )
        if path:
            target_edit.setText(path)
            target_edit.editingFinished.emit()  # trigger any autofill/validation

    def _maybe_autofill_label(self, path_edit: QLineEdit, label_edit: QLineEdit) -> None:
        """
        If label is empty, set from filename stem (sans extension and common suffixes).

        Args:
            path_edit: QLineEdit containing the file path.
            label_edit: QLineEdit to autofill if empty.

        Returns:
            None
        """
        if label_edit.text().strip():
            return
        p = path_edit.text().strip()
        if not p:
            return
        stem: str = os.path.splitext(os.path.basename(p))[0]
        # Remove common noise like timestamps or replicate tags (customize as needed)
        stem = re.sub(
            r'[_\-](rep\d+|v\d+|\d{8,})$', '', stem, flags=re.IGNORECASE)
        label_edit.setText(stem)

    def _validate_inputs(self) -> list[str]:
        """
        Returns a list of error strings. Empty list means valid.

        Args:
            None

        Returns:
            list[str]: List of error messages.
        """
        errors: list[str] = []

        f1 = self.file1_input.text().strip()
        f2 = self.file2_input.text().strip()

        if not f1 or not os.path.isfile(f1):
            errors.append("First file is missing or not a readable path.")
        if not f2 or not os.path.isfile(f2):
            errors.append("Second file is missing or not a readable path.")
        if f1 and not f1.lower().endswith(".tsv"):
            errors.append("First file must be a .tsv.")
        if f2 and not f2.lower().endswith(".tsv"):
            errors.append("Second file must be a .tsv.")
        if f1 and f2 and os.path.abspath(f1) == os.path.abspath(f2):
            errors.append("Please choose two different files.")

        return errors

    def _on_submit(self) -> None:
        """Handle submit button click."""
        errors: list[str] = self._validate_inputs()
        if errors:
            QMessageBox.warning(None, "Invalid input", "\n".join(errors))
            return
        if self.main_app and hasattr(self.main_app, "update_comparison_view"):
            self.main_app.update_comparison_view()

    def _init_toolbar_actions(self) -> None:
        """Initialize toolbar actions for placement in TopBar."""
        # Wrap each widget in a QWidgetAction so TopBar can render them
        def wrap(widget):
            act = QWidgetAction(self)
            act.setDefaultWidget(widget)
            return act

        def spacer(width=20):
            w = QWidget()
            w.setFixedWidth(width)
            return wrap(w)

        self.toolbar_actions.extend([
            wrap(self.file1_text),
            wrap(self.file1_input),
            wrap(self.file1_browse_btn),
            spacer(50),  # spacer between file groups
            wrap(self.file2_text),
            wrap(self.file2_input),
            wrap(self.file2_browse_btn)
        ])

        self.toolbar_actions2.extend([
            wrap(self.library_text),
            wrap(self.library_input),
            spacer(80),  # spacer before button
            wrap(self.submit_button_widget),
            spacer(135),
            wrap(self.export_html_btn)
        ])

    def _on_export_html(self) -> None:
        """Handle export to HTML button click."""
        self.main_app.export_comparison_to_html()
