"""Provides a dialog for selecting top-ranked genes in the enrichment module"""

# --- Third Party Imports ---
from PyQt5.QtWidgets import QDialog, QLineEdit, QPushButton, QVBoxLayout

# --- Public Classes ---


class SelectTopGenesDialog(QDialog):
    """Dialog to select the number of top-ranked genes for enrichment analysis."""

    def __init__(self, parent=None):
        """Initializes the dialog with input field and OK button to select top genes.

        Args:
            parent: Parent QWidget.
        """
        super().__init__(parent)
        self.setWindowTitle("Select Top Genes")
        self.top_genes = 0

        layout = QVBoxLayout()

        self.top_genes_input = QLineEdit()
        self.top_genes_input.setPlaceholderText(
            "Enter number of top genes to select...")
        layout.addWidget(self.top_genes_input)

        select_button = QPushButton("OK")
        select_button.clicked.connect(self.accept_selection)
        layout.addWidget(select_button)

        self.setLayout(layout)

    def accept_selection(self) -> None:
        """Stores the selected number of top genes and closes the dialog."""
        try:
            self.top_genes = int(self.top_genes_input.text())
        except ValueError:
            self.top_genes = 0

        self.accept()
