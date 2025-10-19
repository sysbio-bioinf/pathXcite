"""Provides a dialog for exporting (selected) genes in various formats"""

# --- Third Party Imports ---
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)


# --- Public Classes ---
class ExportDialog(QDialog):
    """Dialog to configure gene export options."""

    def __init__(self, parent=None):
        """Dialog to configure gene export options."""

        super().__init__(parent)
        self.setWindowTitle("Export Genes")
        self.setModal(True)

        self._export_path = ""  # Initialize variable to store export path

        layout = QVBoxLayout()

        # Export all or selected genes
        self.export_all_checkbox = QCheckBox("Export all genes")
        layout.addWidget(self.export_all_checkbox)

        # Export format
        layout.addWidget(QLabel("Export format:"))
        self.export_format_combo = QComboBox()
        self.export_format_combo.addItems(["csv", "txt", "tsv", "json"])
        layout.addWidget(self.export_format_combo)

        # Export symbol or whole row
        self.export_symbol_checkbox = QCheckBox("Export only gene symbols")
        layout.addWidget(self.export_symbol_checkbox)

        # Export path
        self.export_path_button = QPushButton("Select export path")
        self.export_path_button.clicked.connect(self._select_export_path)
        layout.addWidget(self.export_path_button)

        # Buttons
        buttons_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(self.ok_button)
        buttons_layout.addWidget(self.cancel_button)
        layout.addLayout(buttons_layout)

        self.setLayout(layout)

    # --- Public Methods ---
    def _select_export_path(self) -> None:
        """Open a file dialog to select the export path."""
        path, _ = QFileDialog.getSaveFileName(
            self, "Select Export Path", "", "All Files (*)")
        if path:  # Only update if a valid path is selected
            self.export_path = path  # This will use the setter method

    @property
    def export_all(self):
        """Whether to export all genes or only selected ones."""
        return self.export_all_checkbox.isChecked()

    @property
    def export_format(self):
        """The selected export format."""
        return self.export_format_combo.currentText()

    @property
    def export_symbol(self):
        """Whether to export only gene symbols."""
        return self.export_symbol_checkbox.isChecked()

    @property
    def export_path(self):
        """ Getter method for export_path """
        return self._export_path

    @export_path.setter
    def export_path(self, value) -> None:
        """ Setter method for export_path """
        self._export_path = value
        # Update button text with the selected path
        self.export_path_button.setText(value)
