"""A card widget representing a single document in the document selection module"""

# --- Standard Library Imports ---
from collections import defaultdict

# --- Third Party Imports ---
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QCheckBox,
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLayout,
    QListWidget,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

# --- Local Imports ---
from app.util_widgets.clickable_label import ClickableLabel

# --- Public Classes ---


class DocumentCard(QFrame):
    """A card widget representing a single document in the document selection module."""
    expandedChanged = pyqtSignal(bool)
    checkedChanged = pyqtSignal(bool)

    def __init__(self, parent=None):
        """Initialize the DocumentCard widget.
        It displays document metadata and allows expansion/collapse of details.

        Args:
            parent: The parent widget.
        """

        super().__init__(parent)
        self._expanded = True

        # Style
        self.setObjectName("DocumentCard")
        self.setStyleSheet("""
        QFrame#DocumentCard {
            border-radius: 16px;
            border: 1px solid rgba(0,0,0,35);
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                        stop:0 #ffffff, stop:0.07 #f5fbfc, stop:1 #eaf5f8);
        }
        QLabel#title { color: #0b7c87; font: 600 13px "Segoe UI"; }
        QLabel.meta, QLabel.smallmuted { color: #3a3a3a; font: 10pt "Segoe UI"; }
        QLabel.smallmuted { color: #7c7c7c; }
        QLabel.kvkey { color: #7a7a7a; font: italic 10pt "Segoe UI"; }
        #expander { border: none; font: 13px "Segoe UI"; padding: 4px 6px; }
        QToolButton
        QCheckBox { spacing: 8px; }
        """)

        # Header
        self.checkbox = QCheckBox()
        self.checkbox.stateChanged.connect(
            lambda s: self.checkedChanged.emit(bool(s)))

        self.expander = QToolButton(objectName="expander")
        self.expander.setText("▴")
        self.expander.clicked.connect(self._toggle)

        self.ids_label = QLabel()
        self.title_label = QLabel()
        self.title_label.setObjectName("title")
        self.title_label.setWordWrap(True)
        self.title_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.title_label.mousePressEvent = lambda e: self._toggle()
        self.title_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.title_label.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Preferred)

        self.journal_label = QLabel()
        self.pub_type_label = QLabel()
        self.pub_type_label.setAlignment(Qt.AlignRight)
        self.year_label = QLabel()
        self.year_label.setAlignment(Qt.AlignRight)
        self.genes_label = ClickableLabel()
        self.genes_label.setAlignment(Qt.AlignRight)
        self.genes_label.setTextInteractionFlags(Qt.TextBrowserInteraction)

        # Header grid
        header_grid = QGridLayout()
        header_grid.setContentsMargins(12, 12, 12, 0)
        header_grid.setHorizontalSpacing(8)
        header_grid.setRowStretch(1, 1)
        header_grid.setColumnStretch(0, 1)
        header_grid.setColumnStretch(1, 0)
        header_grid.setColumnStretch(2, 0)

        row0 = QHBoxLayout()
        row0.addWidget(self.checkbox)
        row0.addWidget(self.expander)  # make expander visible
        row0.addWidget(self.ids_label)
        row0.addStretch()
        row0.addWidget(self.year_label)

        header_grid.addLayout(row0, 0, 0, 1, 3)
        header_grid.addWidget(self.title_label, 1, 0, 1, 3)
        header_grid.addWidget(self.journal_label, 2, 0, 1, 1)
        header_grid.addWidget(self.pub_type_label, 2, 1, 1, 1)

        # Details
        self.details = QWidget()
        d = QGridLayout(self.details)
        d.setContentsMargins(16, 8, 16, 12)
        d.setHorizontalSpacing(6)
        d.setVerticalSpacing(6)
        d.setColumnStretch(0, 0)
        d.setColumnStretch(1, 1)

        def add_kv(row, key, widget):
            """Helper to add a key-value row to the details grid.

            Args:
                row: The row index.
                key: The key label text.
                widget: The value widget.
            """
            key_label = QLabel(f"{key}:")
            key_label.setProperty("class", "kvkey")
            key_label.setFixedWidth(80)  # adjust as needed
            d.addWidget(key_label, row, 0, Qt.AlignTop)
            d.addWidget(widget, row, 1)

        self.authors_label = ClickableLabel()
        self.authors_label.setWordWrap(True)
        self.doi_label = QLabel()
        self.doi_label.setOpenExternalLinks(True)
        self.mesh_label = ClickableLabel()
        self.mesh_label.setWordWrap(True)
        self.kw_label = ClickableLabel()
        self.kw_label.setWordWrap(True)

        add_kv(0, "Authors", self.authors_label)
        add_kv(1, "doi", self.doi_label)
        add_kv(2, "MeSH Terms", self.mesh_label)
        add_kv(3, "Keywords", self.kw_label)
        add_kv(4, "Genes", self.genes_label)

        # Layout
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSizeConstraint(QLayout.SetDefaultConstraint)
        outer.addLayout(header_grid)
        outer.addWidget(self.details)

        # Shadow
        effect = QGraphicsDropShadowEffect(self)
        effect.setOffset(0, 2)
        effect.setBlurRadius(12)
        effect.setColor(QColor(0, 0, 0, 50))
        self.setGraphicsEffect(effect)

        # Connect clicks to popup
        self.authors_label.clicked.connect(
            lambda: self._show_popup("Authors", self._all_authors))
        self.mesh_label.clicked.connect(
            lambda: self._show_popup("MeSH Terms", self._all_mesh))
        self.kw_label.clicked.connect(
            lambda: self._show_popup("Keywords", self._all_kw))
        self.genes_label.clicked.connect(
            lambda: self._show_gene_popup("Genes", self._all_genes))

        # Keep data refs
        self._all_mesh: list[str] = []
        self._all_kw: list[str] = []
        self._all_genes: list[str] = []
        self._all_authors: list[str] = []

        self.setContentsMargins(7, 7, 7, 7)
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Preferred)

        self.pmid = ""

    # --- Public Methods ---
    def set_data(self, article: dict) -> None:
        """Set the document data to display in the card.

        Args:
            article: A dictionary containing document metadata.
        """
        pmid, pmc = article.get("pubmed_id", ""), article.get("pmc_id", "")
        self.pmid = str(pmid)
        ids = f"PubMed: {pmid}" + (f" ({pmc})" if pmc else "")
        self.ids_label.setText(ids)
        self.title_label.setText(article.get("title", ""))
        self.journal_label.setText(f"Journal: {article.get('journal', '')}")
        self.pub_type_label.setText(
            ", ".join(article.get("publication_type", [])))

        self.journal_label.setWordWrap(True)
        self.pub_type_label.setWordWrap(True)
        self.pub_type_label.setAlignment(Qt.AlignLeft)
        self.pub_type_label.setSizePolicy(
            QSizePolicy.Preferred, QSizePolicy.Preferred)

        self.year_label.setText(str(article.get("year", "")))

        self._all_authors = article.get("authors", [])
        self.authors_label.setText(
            self._format_elide(self._all_authors, max_items=3))

        doi = article.get("doi", "")
        self.doi_label.setText(
            f'<a href="https://doi.org/{doi}">{doi}</a>' if doi else "—")

        # mesh
        self._all_mesh = article.get("mesh_terms", [])
        self.mesh_label.setText(self._format_elide(self._all_mesh, 5))

        # keywords
        self._all_kw = article.get("keywords", [])
        self.kw_label.setText(self._format_elide(self._all_kw, 5))

        # genes
        ann = article.get("annotations", {})
        counts = defaultdict(int)
        for (_, symbol, _), anns in ann.items():
            counts[symbol] += len(anns)
        sorted_genes: list[tuple[str, int]] = sorted(counts.items(),
                                                     key=lambda kv: kv[1], reverse=True)
        self._all_genes = [f"{g} ({c})" for g, c in sorted_genes]
        shown: list[str] = self._all_genes[:5]
        self.genes_label.setText(self._format_elide(
            shown, 5, len(self._all_genes)))

        self.details.setVisible(self._expanded)
        self.adjustSize()
        self.updateGeometry()

    # --- Private Methods ---
    def _show_popup(self, title: str, items: list[str]) -> None:
        """Show a simple list popup for the given items.

        Args:
            title: The dialog title.
            items: The list of string items to display.
        """
        if not items:
            return

        dlg = QDialog(self)
        dlg.setWindowTitle(title)

        layout = QVBoxLayout()
        dlg.setLayout(layout)

        listw = QListWidget()
        listw.addItems(items)

        layout.addWidget(listw)

        btn = QPushButton("Close")
        btn.clicked.connect(dlg.accept)

        layout.addWidget(btn)
        dlg.setModal(True)
        dlg.exec_()

    def _show_gene_popup(self, title: str, items: list[str]) -> None:
        if not items:
            return

        # Parse items into (label, frequency) tuples
        parsed: list[tuple[str, int | None]] = []
        for s in items:
            s = s.strip()
            lparen = s.rfind('(')
            rparen = s.endswith(')')
            if lparen != -1 and rparen:
                label = s[:lparen].rstrip()
                num_str = s[lparen+1:-1].strip()
                try:
                    freq = int(num_str)
                except ValueError:
                    label, freq = s, None
            else:
                label, freq = s, None
            parsed.append((label, freq))

        # Filter out items without a valid integer frequency (keep them, freq=0)
        parsed = [(lbl, (freq if isinstance(freq, int) and freq >= 0 else 0))
                  for lbl, freq in parsed]

        # Sort by frequency descending, then label ascending
        parsed.sort(key=lambda t: (-t[1], t[0].lower()))

        total = sum(freq for _, freq in parsed) or 1  # avoid div/0

        # --- Build dialog ---
        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        dlg.setModal(True)

        layout = QVBoxLayout(dlg)

        table = QTableWidget(len(parsed), 3, dlg)
        table.setHorizontalHeaderLabels(["Item", "Freq", "%"])
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.verticalHeader().setVisible(False)

        # Stretch the first column; size the others to contents
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)

        # Populate rows
        for row, (label, freq) in enumerate(parsed):
            # Item
            it_label = QTableWidgetItem(label)
            it_label.setFlags(it_label.flags() ^ Qt.ItemIsEditable)
            table.setItem(row, 0, it_label)

            # Freq (right-aligned)
            it_freq = QTableWidgetItem(str(freq))
            it_freq.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            it_freq.setFlags(it_freq.flags() ^ Qt.ItemIsEditable)
            table.setItem(row, 1, it_freq)

            # Percentage (right-aligned, 1 decimal)
            pct = (freq / total) * 100.0
            it_pct = QTableWidgetItem(f"{pct:.1f}")
            it_pct.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            it_pct.setFlags(it_pct.flags() ^ Qt.ItemIsEditable)
            table.setItem(row, 2, it_pct)

        layout.addWidget(table)

        # Footer: total + Close button
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        total_btn = QPushButton(f"Total: {total}")
        total_btn.setEnabled(False)
        btn_row.addWidget(total_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dlg.accept)
        btn_row.addWidget(close_btn)

        layout.addLayout(btn_row)

        dlg.resize(720, 480)  # sensible default size
        dlg.exec_()

    def _format_elide(self, items: list[str], max_items: int = 5,
                      total_count: int | None = None) -> str:
        """Format a list of items into a string, eliding if necessary.

        Args:
            items: The list of string items.
            max_items: Maximum number of items to show before replacing with "+N more".
            total_count: Total count of items (if different from len(items)).

        Returns:
            A formatted string with items elided if necessary.
        """
        if not items:
            return "None"
        if total_count is None:
            total_count = len(items)
        if total_count <= max_items:
            return ", ".join(items)
        return ", ".join(items[:max_items]) + f", +{total_count - max_items} more"

    def _toggle(self) -> None:
        """Toggle the expanded/collapsed state of the document card."""
        self._expanded = not self._expanded
        self.details.setVisible(self._expanded)
        self.expander.setText("▴" if self._expanded else "▾")
        self.adjustSize()
        self.updateGeometry()
        self.expandedChanged.emit(self._expanded)

    '''def isExpanded(self) -> bool:
        """Check if the document card is expanded."""
        return self._expanded

    def setExpanded(self, expanded: bool) -> None:
        """Set the expanded/collapsed state of the document card."""
        if self._expanded != expanded:
            self.toggle()'''
