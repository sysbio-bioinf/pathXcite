"""A scrollable box containing DocumentCards for document selection"""

# --- Third Party Imports ---
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QResizeEvent
from PyQt5.QtWidgets import QCheckBox, QScrollArea, QSizePolicy, QVBoxLayout, QWidget

# --- Local Imports ---
from app.enrichment_module.document_selection.document_card import DocumentCard


# --- Public Classes ---
class DocumentBox(QWidget):
    """A vertical list of DocumentCards with spacing and dividers."""

    selectionChanged = pyqtSignal(str, bool)

    def __init__(self, parent=None):
        """Initialize the DocumentBox widget.
        The widget contains a scrollable area with DocumentCards arranged vertically.

        Args:
            parent: The parent widget.
        """
        super().__init__(parent)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.toggle_select_all = QCheckBox("Select/Deselect All")
        self.toggle_select_all.stateChanged.connect(self._on_toggle_select_all)
        self.main_layout.addWidget(self.toggle_select_all)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.container = QWidget()
        self.container.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.container.setMinimumWidth(200)

        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(12, 12, 12, 12)
        self.container_layout.setSpacing(10)
        self.container_layout.addStretch(1)

        self.scroll_area.setWidget(self.container)
        self.main_layout.addWidget(self.scroll_area)

        self._card_by_pmid: dict[str, DocumentCard] = {}

        self.article_ids: list[str] = []
        self.article_data: list[dict] = []

    # -- Public Methods ---
    def update_documents(self, articles: list[dict]) -> None:
        """Replace current documents with new ones."""
        # Clear container layout (but keep the trailing stretch)
        while self.container_layout.count() > 1:
            item = self.container_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        self._card_by_pmid.clear()

        for article in articles:
            card = DocumentCard()
            card.set_data(article)
            card.checkedChanged.connect(lambda checked,
                                        c=card: self.selectionChanged.emit(c.pmid, checked))
            # keep in map
            self._card_by_pmid[card.pmid] = card
            # insert before the final stretch
            self.container_layout.insertWidget(
                self.container_layout.count() - 1, card)

    def set_all_checked(self, checked: bool) -> None:
        """Set all document cards to checked/unchecked state."""
        self.toggle_select_all.blockSignals(True)
        self.toggle_select_all.setChecked(
            Qt.Checked if checked else Qt.Unchecked)
        self.toggle_select_all.blockSignals(False)
        # set card checkboxes (will emit selectionChanged via our wiring)
        for card in self._iter_cards():
            card.checkbox.setChecked(checked)

    # --- Private Methods ---
    def _on_toggle_select_all(self, state: int) -> None:
        """Handle the 'Select/Deselect All' checkbox state change."""
        check = state == Qt.Checked

        for card in self._iter_cards():
            card.checkbox.setChecked(check)

    def _iter_cards(self):
        """Iterator over all DocumentCards in the container layout."""
        for i in range(self.container_layout.count() - 1):
            w: DocumentCard = self.container_layout.itemAt(i).widget()
            if isinstance(w, DocumentCard):
                yield w

    '''def resize_event(self, e: QResizeEvent) -> None:
        """Handle resize events to adjust DocumentCard widths."""
        super().resizeEvent(e)
        vw = self.scroll_area.viewport().width()

        for card in self._iter_cards():
            card.setMaximumWidth(vw)'''
