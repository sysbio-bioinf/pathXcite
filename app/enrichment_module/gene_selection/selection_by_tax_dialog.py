"""Provides a dialog for selecting genes based on multiple Tax IDs in the enrichment module"""

# --- Third Party Imports ---
from PyQt5.QtWidgets import (
    QDialog,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

# --- Public Classes ---


class TaxIdSelectionDialog(QDialog):
    """Dialog to select Tax IDs for enrichment analysis."""

    def __init__(self, tax_id_list: list[str], parent=None):
        """Initializes the dialog with a list of Tax IDs for selection.

        Args:
            tax_id_list: List of Tax IDs to display.
            parent: Parent QWidget.
        """
        super().__init__(parent)
        self.setWindowTitle("Select Tax IDs")
        self.selected_tax_ids = set()

        layout = QVBoxLayout()

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.MultiSelection)

        for tax_id in sorted(set(tax_id_list)):  # Unique and sorted tax IDs
            item = QListWidgetItem(str(tax_id))
            self.list_widget.addItem(item)

        layout.addWidget(self.list_widget)

        select_button = QPushButton("OK")
        select_button.clicked.connect(self.accept_selection)
        layout.addWidget(select_button)

        self.setLayout(layout)

    def accept_selection(self) -> None:
        """Stores the selected Tax IDs and closes the dialog."""
        self.selected_tax_ids = {item.text()
                                 for item in self.list_widget.selectedItems()}
        self.accept()
