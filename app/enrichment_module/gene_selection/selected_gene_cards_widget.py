"""Provides a widget for displaying selected genes as cards with details and sections"""

# --- Standard Library Imports ---
import sqlite3

# --- Third Party Imports ---
from PyQt5.QtCore import QModelIndex, Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListView,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedLayout,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

# --- Local Imports ---
from app.enrichment_module.gene_selection.gene_list_model import GeneListModel
from app.enrichment_module.gene_selection.gene_proxy import GeneProxy
from app.enrichment_module.gene_selection.gene_roles import GeneRoles
from app.enrichment_module.gene_selection.narrow_gene_delegate import NarrowGeneDelegate


# # --- Public Classes ---
class SelectedGeneCardsWidget(QWidget):
    """Widget to display selected genes as cards with details and sections."""
    selectionChanged = pyqtSignal(dict)

    def __init__(self, selected_genes: list[str] = None, parent=None):
        """Initialize the widget with selected genes.

        It displays a list of genes, allows sorting and filtering,
        and shows detailed information and sections for each gene.

        Args:
            selected_genes(list of dict): Initial list of selected gene data.
            parent: Parent QWidget.
        """
        super().__init__(parent)
        self._data: list[str] = selected_genes or []
        self._db_path: str = None
        self._current_gene: dict = None
        self._last_grouped_sections: list[dict] = None  # cache for filtering

        self.stack = QStackedLayout(self)

        # -------- Page 0: List --------
        list_page = QFrame(self)
        list_layout = QVBoxLayout(list_page)
        list_layout.setContentsMargins(5, 5, 5, 5)
        list_layout.setSpacing(5)

        gene_selection_bar = QFrame(list_page)
        bar_layout = QHBoxLayout(gene_selection_bar)
        bar_layout.setContentsMargins(8, 6, 8, 6)
        bar_layout.setSpacing(6)
        self.title_label = QLabel("No Selected Genes")
        self.header_mode = QComboBox(self)
        self.header_mode.addItems(["Symbol + Entrez", "Symbol", "Entrez ID"])
        self.sort_combo = QComboBox(self)
        self.sort_combo.addItems(
            ["Annotations (desc)", "GF-IDF (desc)", "Symbol", "Entrez ID"])
        bar_layout.addWidget(self.title_label)
        bar_layout.addStretch(1)
        bar_layout.addWidget(self.header_mode)
        bar_layout.addWidget(self.sort_combo)
        list_layout.addWidget(gene_selection_bar)

        # stat chips (scroll horizontally)
        self.stats_scroll = QScrollArea(list_page)
        self.stats_scroll.setWidgetResizable(True)
        self.stats_scroll.setFixedHeight(44)
        stats_inner = QFrame(self.stats_scroll)
        stats_inner_layout = QHBoxLayout(stats_inner)
        stats_inner_layout.setContentsMargins(8, 4, 8, 4)
        stats_inner_layout.setSpacing(6)
        self._chips = {k: self._make_chip(
            k, "-") for k in ["Genes", "Ann.", "Taxa", "Median", "Top"]}
        for chip in self._chips.values():
            stats_inner_layout.addWidget(chip)
        stats_inner_layout.addStretch(1)
        self.stats_scroll.setWidget(stats_inner)
        list_layout.addWidget(self.stats_scroll)

        self.search_edit = QLineEdit(list_page)
        self.search_edit.setPlaceholderText(
            "Filter... (toggle deep search for annotations)")
        list_layout.addWidget(self.search_edit)
        self.deep_search = QCheckBox("Deep search")
        list_layout.addWidget(self.deep_search)

        self.list_view = QListView(list_page)
        self.list_view.setUniformItemSizes(True)
        self.list_view.setVerticalScrollMode(QListView.ScrollPerPixel)
        self.list_view.setSelectionMode(QListView.SingleSelection)
        self.list_view.setSpacing(3)  # extra spacing between gene rows
        list_layout.addWidget(self.list_view, 1)

        self.stack.addWidget(list_page)

        # -------- Page 1: Detail --------
        detail_page = QFrame(self)
        detail_layout = QVBoxLayout(detail_page)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_layout.setSpacing(0)
        detail_bar = QFrame(detail_page)
        detail_h_layout = QHBoxLayout(detail_bar)
        detail_h_layout.setContentsMargins(8, 6, 8, 6)
        detail_h_layout.setSpacing(6)
        self.back_btn = QPushButton("← Back")
        self.copy_sym_btn = QPushButton("Copy Symbol")
        self.copy_ent_btn = QPushButton("Copy Entrez")
        self.show_sections_btn = QPushButton("Show Sections")
        self.detail_title = QLabel("")
        detail_h_layout.addWidget(self.back_btn)
        detail_h_layout.addWidget(self.detail_title, 1)
        detail_h_layout.addWidget(self.copy_sym_btn)
        detail_h_layout.addWidget(self.copy_ent_btn)
        detail_h_layout.addWidget(self.show_sections_btn)
        detail_layout.addWidget(detail_bar)

        self.detail_scroll = QScrollArea(detail_page)
        self.detail_scroll.setWidgetResizable(True)
        self.detail_frame = QFrame(self.detail_scroll)
        self.detail_layout = QVBoxLayout(self.detail_frame)
        self.detail_layout.setContentsMargins(12, 12, 12, 12)
        self.detail_layout.setSpacing(12)
        self.detail_scroll.setWidget(self.detail_frame)
        detail_layout.addWidget(self.detail_scroll, 1)

        self.stack.addWidget(detail_page)

        # -------- Page 2: Sections (cards per document) --------
        sections_page = QFrame(self)
        sections_layout = QVBoxLayout(sections_page)
        sections_layout.setContentsMargins(0, 0, 0, 0)
        sections_layout.setSpacing(0)

        # header bar
        sections_bar = QFrame(sections_page)
        sections_bar_layout = QHBoxLayout(sections_bar)
        sections_bar_layout.setContentsMargins(8, 6, 8, 6)
        sections_bar_layout.setSpacing(6)
        self.back_from_sections_btn = QPushButton("← Back")
        self.sections_title = QLabel("Sections")
        self.pmid_filter_edit = QLineEdit()
        self.pmid_filter_edit.setPlaceholderText("Filter by PMID (optional)")
        self.sections_search_edit = QLineEdit()
        self.sections_search_edit.setPlaceholderText(
            "Search in title/section/text…")
        sections_bar_layout.addWidget(self.back_from_sections_btn)
        sections_bar_layout.addWidget(self.sections_title, 1)
        sections_bar_layout.addWidget(self.pmid_filter_edit)
        sections_bar_layout.addWidget(self.sections_search_edit)
        sections_layout.addWidget(sections_bar)

        # summary chips
        self.sections_chips = QFrame(sections_page)
        cbl = QHBoxLayout(self.sections_chips)
        cbl.setContentsMargins(8, 4, 8, 4)
        cbl.setSpacing(8)
        self._pchips = {k: self._make_chip(
            k, "-") for k in ["Docs", "Unique Sections", "Mentions"]}
        for chip in self._pchips.values():
            cbl.addWidget(chip)
        cbl.addStretch(1)
        sections_layout.addWidget(self.sections_chips)

        # scrollable card container
        self.sections_scroll = QScrollArea(sections_page)
        self.sections_scroll.setWidgetResizable(True)
        self.sections_container = QFrame(self.sections_scroll)
        self.sections_cards_layout = QVBoxLayout(self.sections_container)
        self.sections_cards_layout.setContentsMargins(12, 12, 12, 12)
        self.sections_cards_layout.setSpacing(18)
        self.sections_cards_layout.addStretch(1)
        self.sections_scroll.setWidget(self.sections_container)
        sections_layout.addWidget(self.sections_scroll, 1)

        self.stack.addWidget(sections_page)

        # Models (genes)
        self._model = GeneListModel(self._data, self)
        self._proxy = GeneProxy(self)
        self._proxy.setSourceModel(self._model)
        self.list_view.setModel(self._proxy)
        self._delegate = NarrowGeneDelegate(
            self.header_mode.currentText, self.list_view)
        self.list_view.setItemDelegate(self._delegate)

        # Wire
        self.header_mode.currentTextChanged.connect(
            lambda _: self._proxy.set_header_mode(self.header_mode.currentText()))
        self.sort_combo.currentTextChanged.connect(self._proxy.set_sort_mode)
        self.search_edit.textChanged.connect(self._proxy.setFilterRegExp)
        self.deep_search.toggled.connect(self._proxy.set_deep_search)
        self.list_view.clicked.connect(self._open_detail)
        self.back_btn.clicked.connect(lambda: self.stack.setCurrentIndex(0))

        # sections page wiring
        self.show_sections_btn.clicked.connect(
            self._open_sections_for_current_gene)
        self.back_from_sections_btn.clicked.connect(
            lambda: self.stack.setCurrentIndex(1))
        self.sections_search_edit.textChanged.connect(
            self._filter_section_cards)
        self.pmid_filter_edit.textChanged.connect(self._filter_section_cards)

        # Init
        self._proxy.set_sort_mode(self.sort_combo.currentText())
        self._refresh_stats_and_title()
        if self._proxy.rowCount() > 0:
            self.list_view.setCurrentIndex(self._proxy.index(0, 0))

        # compact styles
        self.setStyleSheet("""
        QListView {border: none;}
        # Chip { border: 1px solid palette(mid); border-radius: 10px; background: palette(base); padding: 2px 8px; }
        QFrame
        QLabel  # ChipText { font-weight: 600; }
        """)

    # ---- Public API ----
    def update_data(self, genes: list[dict], db_path: str = None) -> None:
        """
        Update the widget with a new list of selected genes.

        Args:
            genes: list of gene dicts(same structure as before)
            db_path: path to the sqlite3 database(enables sections page)
        """
        self._data: list[dict] = genes or []
        if db_path is not None:
            self._db_path = str(db_path)
        self._model.update(self._data)
        self._proxy.invalidate()
        self._proxy.set_sort_mode(self.sort_combo.currentText())
        self._refresh_stats_and_title()

    # ---- Internals: chips & stats ----
    def _make_chip(self, label: str, value: str) -> QFrame:
        """ Create a stat chip with label and value.

        Args:
            label: Label text.
            value: Initial value text.

        Returns:
            QFrame representing the chip.
        """
        chip = QFrame(self)
        chip.setObjectName("Chip")
        h = QHBoxLayout(chip)
        h.setContentsMargins(8, 2, 8, 2)
        h.setSpacing(6)
        t = QLabel(label + ":")
        v = QLabel(value)
        v.setObjectName("ChipText")
        h.addWidget(t)
        h.addWidget(v)
        chip._value = v
        return chip

    def _set_chip(self, key: str, value: str) -> None:
        """ Update the value of a stat chip.

        Args:
            key: Chip label.
            value: New value to set.
        """
        self._chips[key]._value.setText(str(value))

    def _set_pchip(self, key: str, value: str) -> None:
        """ Update the value of a section page stat chip.
        Args:
            key: Chip label.
            value: New value to set.
        """
        self._pchips[key]._value.setText(str(value))

    def _refresh_stats_and_title(self) -> None:
        """ Recalculate and update stats and title based on current data."""
        d: list[dict] = self._data or []
        n = len(d)
        self.title_label.setText(f"{n} Genes" if n else "No Genes")
        total_ann = sum(int(x.get("annotations", 0) or 0) for x in d)
        taxa = set(str(x.get("tax_id", "") or "")
                   for x in d if x.get("tax_id"))
        ann_counts = sorted([int(x.get("annotations", 0) or 0) for x in d])
        if not ann_counts:
            median_value = 0
        else:
            n = len(ann_counts)
            mid = n // 2
            median_value = ann_counts[mid] if n % 2 else (
                ann_counts[mid - 1] + ann_counts[mid]) / 2

        top = max(d, key=lambda x: int(
            x.get("annotations", 0) or 0), default=None)
        top_gene = (top.get("gene_symbol") or top.get(
            "entrez_id")) if top else "-"
        self._set_chip("Genes", n)
        self._set_chip("Ann.", total_ann)
        self._set_chip("Taxa", len(taxa))
        self._set_chip("Median", f"{median_value:.1f}" if isinstance(
            median_value, float) else str(median_value))
        self._set_chip("Top", top_gene)

    # ---- Detail page ----
    def _clear_detail(self) -> None:
        """ Clear the detail layout of previous widgets. """
        while self.detail_layout.count():
            it = self.detail_layout.takeAt(0)
            w = it.widget()
            if w:
                w.deleteLater()

    def _open_detail(self, proxy_index: QModelIndex) -> None:
        """ Open the detail view for the selected gene.

        Args:
            proxy_index: QModelIndex from the proxy model.
        """

        src = self._proxy.mapToSource(proxy_index)
        g = self._model.data(src, GeneRoles.DATA)
        self._current_gene = g
        self._clear_detail()
        sym = g.get('gene_symbol', '')
        ent = g.get('entrez_id', '')
        self.detail_title.setText(f"{sym}; {ent}" if (
            sym and ent) else (sym or ent or "(gene)"))
        self.copy_sym_btn.clicked.connect(
            lambda _, s=sym: QApplication.clipboard().setText(s))
        self.copy_ent_btn.clicked.connect(
            lambda _, e=ent: QApplication.clipboard().setText(e))
        info = QLabel(
            f"{g.get('annotations', 0)} ann; GF-IDF {float(g.get('gfidf', 0.0)):.3f}; {g.get('tax_id', '')}")
        self.detail_layout.addWidget(info)
        table = build_annotation_table(self, g.get("annotation_list") or [])
        table.setHorizontalScrollMode(table.ScrollPerPixel)
        self.detail_layout.addWidget(table, 1)
        self.stack.setCurrentIndex(1)
        self.selectionChanged.emit(g)

    # ---- Sections page: data + rendering ----
    def _open_sections_for_current_gene(self) -> None:
        """ Open the sections page for the current gene, fetching and rendering data. """
        if not self._current_gene:
            return
        sym = self._current_gene.get('gene_symbol', '')
        ent = self._current_gene.get('entrez_id', '')
        title = sym or ent or "gene"
        self.sections_title.setText(f"Sections for {title}")

        grouped = self._fetch_sections_grouped_for_gene(self._current_gene)
        self._last_grouped_sections = grouped  # cache for live filtering
        self.sections_search_edit.clear()
        self.pmid_filter_edit.clear()
        self._render_section_cards(grouped)
        self.stack.setCurrentIndex(2)

    def _filter_section_cards(self) -> None:
        """ Re-render section cards based on current filter inputs. """
        if not self._last_grouped_sections:
            return
        self._render_section_cards(self._last_grouped_sections)

    def _clear_section_cards(self) -> None:
        """ Clear all section cards from the layout except the final stretch. """
        while self.sections_cards_layout.count() > 1:  # keep the final stretch
            it = self.sections_cards_layout.takeAt(0)
            w = it.widget()
            if w:
                w.deleteLater()

    def _render_section_cards(self, grouped: dict) -> None:
        """ Render section cards based on grouped data and current filters.

        Args:
            grouped: dict returned by _fetch_sections_grouped_for_gene
        """
        self._clear_section_cards()

        # summary
        self._set_pchip("Docs", grouped["summary"]["n_documents"])
        self._set_pchip("Unique Sections",
                        grouped["summary"]["n_unique_sections"])
        self._set_pchip("Mentions", grouped["summary"]["total_mentions"])

        q = (self.sections_search_edit.text() or "").lower().strip()
        pmid_filter = (self.pmid_filter_edit.text() or "").strip()

        # Each document card
        for doc in grouped["docs"]:
            if pmid_filter and doc["pubmed_id"] != pmid_filter:
                continue

            # Filter sections by search query
            def match_section(p, d):
                if not q:
                    return True
                hay = " ".join([
                    d.get("title", ""),
                    str(d.get("pubmed_id", "")),
                    p.get("section_type", ""),
                    p.get("type", ""),
                    p.get("section_text", "")
                ]).lower()
                return q in hay

            filtered_sections = [
                p for p in doc["sections"] if match_section(p, doc)]
            if not filtered_sections:
                continue

            # Document card
            card = QFrame(self.sections_container)
            card.setObjectName("DocCard")
            card.setStyleSheet(
                """QFrame  # DocCard { border: 1px solid palette(mid);
                border-radius: 8px; background: palette(base); }""")
            cl = QVBoxLayout(card)
            cl.setContentsMargins(12, 12, 12, 12)
            cl.setSpacing(12)

            header = QLabel(f"<b>PMID {doc['pubmed_id']}</b> — {doc['title'] or '(no title)'} "
                            f"<span style='color:gray'>• {doc['total_mentions']} mentions</span>")
            header.setTextFormat(Qt.RichText)
            cl.addWidget(header)

            # Each unique section ordered
            for p in filtered_sections:
                row = QFrame(card)
                rl = QVBoxLayout(row)
                rl.setContentsMargins(8, 8, 8, 8)
                rl.setSpacing(6)

                meta = QLabel(
                    f"s{p['section_number']} ({p['section_type'] or p['type']}): <b>{p['count']}x</b>")
                meta.setTextFormat(Qt.RichText)
                rl.addWidget(meta)

                body = QLabel(p['section_text'])
                body.setWordWrap(True)
                rl.addWidget(body)

                # soft divider
                sub = QFrame(card)
                sub.setFrameShape(QFrame.HLine)
                sub.setFrameShadow(QFrame.Sunken)
                rl.addWidget(sub)

                cl.addWidget(row)

            self.sections_cards_layout.insertWidget(
                self.sections_cards_layout.count()-1, card)

    def _fetch_sections_grouped_for_gene(self, gene: dict) -> dict:
        """
        Build per-document cards with unique sections and counts.

        Args:
            gene: gene dict as in the selected genes list.
        Returns:
        {
          "summary": {"n_documents": int, "n_unique_sections": int, "total_mentions": int},
          "docs": [
            {
              "pubmed_id": "12345",
              "title": "Title...",
              "total_mentions": 7,
              "sections": [
                {"section_number": 1, "section_type": "ABSTRACT", "type": "abstract",
                 "section_text": "full text ...", "count": 3},
                ...
              ]
            },
            ...
          ]
        }
        """
        if not self._db_path:
            return {"summary": {"n_documents": 0,
                                "n_unique_sections": 0,
                                "total_mentions": 0},
                    "docs": []
                    }

        entrez = (gene.get("entrez_id") or "").strip()
        accs = sorted({a.get("accession") for a in (
            gene.get("annotation_list") or []) if a.get("accession")})
        base = """
            SELECT a.pubmed_id, ar.title,
                   a.passage_number, p.section_type, p.type, p.passage_text,
                   COUNT(*) as mention_count
            FROM annotations a
            JOIN passages p ON a.pubmed_id = p.pubmed_id AND a.passage_number = p.passage_number
            LEFT JOIN articles ar ON ar.pubmed_id = a.pubmed_id
            WHERE {COND}
            GROUP BY a.pubmed_id, a.passage_number
            ORDER BY a.pubmed_id, a.passage_number
        """
        rows: list[tuple] = []
        try:
            conn = sqlite3.connect(self._db_path)
            cur = conn.cursor()

            # Fast path: by numeric entity_id (preferred)
            if entrez and entrez.isdigit():
                cur.execute(base.format(COND="a.entity_id = ?"), (entrez,))
                rows = cur.fetchall()

            # Fallback: by accession(s)
            if (not rows) and accs:
                q = base.format(COND="a.accession IN ({})".format(
                    ",".join(["?"]*len(accs))))
                cur.execute(q, tuple(accs))
                rows = cur.fetchall()

            # Last resort: by symbol via entities join
            if not rows:
                sym = (gene.get("gene_symbol") or "").strip()
                if sym:
                    q = base.replace(
                        "WHERE {COND}",
                        """WHERE a.entity_id IN (
                        SELECT e.entity_id FROM entities e 
                        WHERE e.biotype='gene' 
                        AND (e.name=? OR e.accession=?)
                        )
                        """
                    )
                    cur.execute(q, (sym, f"@GENE_{sym}"))
                    rows = cur.fetchall()

            conn.close()
        except sqlite3.Error as e:
            print(f"[Sections grouped query error] {e}")
            rows: list[tuple] = []

        # Build doc → sections and summary
        docs_map: dict[str, dict] = {}
        total_mentions = 0
        for (pmid, title, pno, sec, typ, ptxt, cnt) in rows:
            d = docs_map.setdefault(str(pmid), {
                "pubmed_id": str(pmid),
                "title": title or "",
                "sections": [],
                "total_mentions": 0
            })
            d["sections"].append({
                "section_number": pno,
                "section_type": sec or "",
                "type": typ or "",
                "section_text": ptxt or "",
                "count": int(cnt or 0)
            })
            d["total_mentions"] += int(cnt or 0)
            total_mentions += int(cnt or 0)

        for d in docs_map.values():
            d["sections"].sort(key=lambda x: (
                x["section_number"] if x["section_number"] is not None else 10**9))

        docs = sorted(docs_map.values(), key=lambda d: d["pubmed_id"])
        n_docs = len(docs)
        n_unique_sections = sum(len(d["sections"]) for d in docs)

        return {
            "summary": {
                "n_documents": n_docs,
                "n_unique_sections": n_unique_sections,
                "total_mentions": total_mentions
            },
            "docs": docs
        }


# --- Helper Functions ---
def build_annotation_table(parent: QWidget, ann_list: list[dict]) -> QTableWidget:
    """ Build a QTableWidget for the given annotation list.

    Args:
        parent: Parent QWidget.
        ann_list: List of annotation dicts.
    Returns:
        QTableWidget populated with annotation data.
    """
    cols = ["text", "accession", "pubmed_id",
            "section_number", "offset_start", "length", "tax_id"]
    t = QTableWidget(len(ann_list), len(cols), parent)
    t.setHorizontalHeaderLabels([c.replace("_", " ").title() for c in cols])
    t.verticalHeader().setVisible(False)
    t.setEditTriggers(QTableWidget.NoEditTriggers)
    t.setSelectionBehavior(QTableWidget.SelectRows)
    t.setSelectionMode(QTableWidget.SingleSelection)
    t.setAlternatingRowColors(True)
    t.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    for r, item in enumerate(ann_list):
        for c, key in enumerate(cols):

            val = item.get(key)
            if key == "section_number" and val is None:
                val = item.get("passage_number")

            it = QTableWidgetItem("" if val is None else str(val))
            if key in {"section_number", "offset_start", "length"}:
                it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            t.setItem(r, c, it)

    t.resizeColumnsToContents()
    t.horizontalHeader().setStretchLastSection(True)
    t.setMinimumHeight(280)
    return t
