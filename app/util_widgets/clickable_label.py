"""A QLabel that emits a signal when clicked"""

# --- Third Party Imports ---
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QLabel


# --- Public Classes ---
class ClickableLabel(QLabel):
    """A label that emits clicked() when pressed."""
    clicked = pyqtSignal()

    def mousePressEvent(self, event):
        """Override mousePressEvent to emit clicked signal on left button press."""
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
