"""Provides a custom QTableWidgetItem for numeric sorting in gene selection tables"""

# --- Third Party Imports ---
from PyQt5.QtWidgets import QTableWidgetItem


# --- Public Classes ---
class NumericGeneTableWidgetItem(QTableWidgetItem):
    """Custom QTableWidgetItem to force numerical sorting."""

    def __init__(self, value):
        super().__init__(str(value))
        self.value = value  # Store the numeric value

    def __lt__(self, other):
        if isinstance(other, NumericGeneTableWidgetItem):
            return self.value < other.value
        return super().__lt__(other)
