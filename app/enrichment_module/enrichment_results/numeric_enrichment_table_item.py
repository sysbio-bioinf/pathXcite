"""Provides a custom QTableWidgetItem for numeric sorting in enrichment results tables"""

# --- Third Party Imports ---
from PyQt5.QtWidgets import QTableWidgetItem


# --- Public Classes ---
class NumericEnrichmentTableWidgetItem(QTableWidgetItem):
    """Custom QTableWidgetItem to force numerical sorting."""

    def __init__(self, value, display_text):
        super().__init__(display_text)  # Display the text
        self.value = value  # Store the actual numeric value

    def __lt__(self, other):
        """Ensure numerical sorting for numeric values."""
        if isinstance(other, NumericEnrichmentTableWidgetItem):
            return self.value < other.value
        return super().__lt__(other)  # Default behavior
