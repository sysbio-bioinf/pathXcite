"""A QLineEdit that accepts drag & drop of .tsv files"""

# --- Third Party Imports ---
from PyQt5.QtWidgets import QLineEdit


# --- Public Classes ---
class PathDropLineEdit(QLineEdit):
    """
    Compact line edit that accepts drag & drop of .tsv files.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAcceptDrops(True)
        self.setClearButtonEnabled(True)

    # --- Public Functions ---
    def dragEnterEvent(self, event) -> None:
        """Accept drag if it contains .tsv files."""
        if event.mimeData().hasUrls() and any(
            u.toLocalFile().lower().endswith('.tsv') for u in event.mimeData().urls()
        ):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:
        """Handle drop event for .tsv files."""
        for u in event.mimeData().urls():
            path = u.toLocalFile()
            if path.lower().endswith('.tsv'):
                self.setText(path)
                self.editingFinished.emit()
                break
        event.acceptProposedAction()
