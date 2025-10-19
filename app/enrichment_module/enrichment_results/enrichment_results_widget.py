"""Provides the enrichment results widget for the enrichment module"""

# --- Third Party Imports ---
import pandas as pd
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QMenu,
    QMenuBar,
    QMessageBox,
    QScrollArea,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

# --- Local Imports ---
from app.util_widgets.icon_line_edit import IconLineEdit
from app.util_widgets.svg_button import SvgHoverButton
from app.utils import get_default_html_svg, resource_path


# --- Public Classes ---
class EnrichmentResultsWidget(QWidget):
    """Single-class widget: shows an HTML intro page or a sortable enrichment results table."""

    # --- small helper for numeric sorting in QTableWidget
    class NumericTableWidgetItem(QTableWidgetItem):
        """Custom QTableWidgetItem for numeric sorting."""

        def __init__(self, value, display_text):
            super().__init__(display_text)
            self.value = value

        def __lt__(self, other):
            if isinstance(other, EnrichmentResultsWidget.NumericTableWidgetItem):
                return self.value < other.value
            return super().__lt__(other)

    PAGE_INIT = 0
    PAGE_TABLE = 1

    def __init__(self, main_app, dataframe):
        """Initialize the enrichment results widget.

        Args:
            main_app: Reference to the main application.
            dataframe: Initial pandas DataFrame to display (or None).
        """
        super().__init__()
        self.main_app = main_app
        self.dataframe = None  # processed df currently rendered

        # ===== Layout & stacked pages =====
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self.stacked_widget)

        # ----- Page 0: HTML init/info page
        self.init_page = self.main_app.get_new_web_view(parent=self)
        html = get_default_html_svg(
            str(resource_path("assets/icons/lightbulb.svg")),
            "Please start enrichment process to get insights into enriched pathways."
        )
        self.init_page.setHtml(html)
        self.stacked_widget.addWidget(self.init_page)  # index 0

        # ----- Page 1: Table view page
        self.table_view_widget = QWidget()
        table_page_layout = QVBoxLayout(self.table_view_widget)

        # Toolbar
        self.menu_bar = QMenuBar()
        self.menu = QMenu("Actions", self)
        self.menu_bar.addMenu(self.menu)
        table_page_layout.addWidget(self.menu_bar)

        self.search_term = IconLineEdit(
            "filter", tooltip="Type to filter",
            on_text_changed=self._filter_table, icon_size=22, icon_position="right"
        )
        self.search_term.setPlaceholderText("Type to filter...")
        self.search_term.setFixedHeight(30)
        self.search_term.setMinimumWidth(200)

        self.search_type = QComboBox()
        self.search_type.setFixedHeight(30)
        self.search_type.addItems(["Term", "Gene"])
        self.search_type.currentIndexChanged.connect(self._filter_table)

        self.export_gene_btn = SvgHoverButton(
            base_name="export",
            tooltip="Save Enrichment Results",
            triggered_func=lambda: self._save_results(),
            size=20,
            parent=self
        )

        term_toolbar = QWidget()
        term_toolbar_layout = QHBoxLayout(term_toolbar)
        term_toolbar_layout.setContentsMargins(0, 0, 0, 0)
        term_toolbar_layout.setSpacing(5)
        term_toolbar_layout.addWidget(self.search_term)
        term_toolbar_layout.addWidget(self.search_type)
        term_toolbar_layout.addStretch()
        term_toolbar_layout.addWidget(self.export_gene_btn)
        table_page_layout.addWidget(term_toolbar)

        # Table
        self.table_scroll = QScrollArea()

        self.table = QTableWidget()
        self.table.setSortingEnabled(True)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().sectionResized.connect(self._adjust_number_precision)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.table_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.table_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.table_scroll.setWidgetResizable(True)
        self.table_scroll.setWidget(self.table)
        table_page_layout.addWidget(self.table_scroll)

        self.stacked_widget.addWidget(self.table_view_widget)  # index 1

        # Initial data / view
        self.set_dataframe(dataframe)

    # --- Public Methods ---
    def set_dataframe(self, dataframe: pd.DataFrame | None) -> None:
        """
        Replace the current table content with a new dataframe (or None).
        Automatically switches between the HTML page and the table page.

        Args:
            dataframe (pd.DataFrame | None): New dataframe to display, or None for no data

        """
        header = self.table.horizontalHeader()
        sort_col = header.sortIndicatorSection()
        sort_ord = header.sortIndicatorOrder()
        was_sorting = self.table.isSortingEnabled()
        self.table.setSortingEnabled(False)

        try:
            # avoid doing filtering while loading
            self.search_term.blockSignals(True)
            self.search_term.clear()
            self.search_term.blockSignals(False)
            self.table.clearSelection()

            # (re)build table from df
            self._load_data(dataframe)

            # restore previous sort if it still makes sense
            if self._has_data() and 0 <= sort_col < self.table.columnCount():
                self.table.sortItems(sort_col, sort_ord)

            self.table.resizeColumnsToContents()

        finally:
            self.table.setSortingEnabled(was_sorting)
            # sort by Adjusted P-value if present
            if self._has_data():
                adj_p_col = -1
                for c in range(self.table.columnCount()):
                    if self.table.horizontalHeaderItem(c).text() == "Adjusted P-value":
                        adj_p_col = c
                        break
                if adj_p_col >= 0:
                    self.table.sortItems(adj_p_col, Qt.AscendingOrder)

        # swap stacked page
        self._update_view_state()

    def update_html(self, message: str) -> None:
        """
        Update the HTML content of the init page with a new message.

        Args:
            message (str): New message to display.
        """
        self.init_page.setHtml(get_default_html_svg(
            str(resource_path("assets/icons/lightbulb.svg")), message))

    def show_context_menu(self, pos) -> None:
        """Show context menu at the given position."""
        menu = QMenu(self)
        copy_action = QAction("Copy to Clipboard", self)
        copy_action.triggered.connect(self._copy_to_clipboard)
        menu.addAction(copy_action)

        column_menu = menu.addMenu("Show/Hide Columns")
        for col in range(self.table.columnCount()):
            column_name = self.table.horizontalHeaderItem(col).text()
            action = QAction(column_name, self, checkable=True)
            action.setChecked(not self.table.isColumnHidden(col))
            action.triggered.connect(
                lambda checked, idx=col: self._toggle_column_visibility(idx, checked))
            column_menu.addAction(action)

        menu.exec_(self.table.viewport().mapToGlobal(pos))

    # --- Private Methods ---

    def _has_data(self) -> bool:
        """Check if there is data to show in the table."""
        return self.dataframe is not None and not getattr(self.dataframe, "empty", True)

    def _update_view_state(self) -> None:
        """Switch between init page and table page based on data availability."""
        self.stacked_widget.setCurrentIndex(
            self.PAGE_TABLE if self._has_data() else self.PAGE_INIT)

    def _load_data(self, dataframe: pd.DataFrame | None) -> None:
        """
        Build the table. Keeps a processed copy in self.dataframe for rendering/filtering.

        Args:
            dataframe (pd.DataFrame | None): DataFrame to load into the table.
        """
        # always keep what is asked to eb shown (even if empty)
        self.dataframe = dataframe

        # Handle empty / None early: clear table, leave page switching to caller.
        if dataframe is None or getattr(dataframe, "empty", True):
            self.table.setRowCount(0)
            self.table.setColumnCount(0)
            return

        # Drop excluded columns if present
        excluded = {"Old P-value", "Old Adjusted P-value",
                    "Term Size", "Query Size", "Count", "Background Size"}
        dataframe = dataframe.drop(
            columns=[c for c in excluded if c in dataframe], errors='ignore')

        # Move "Genes" to the end if present
        if 'Genes' in dataframe.columns:
            cols = [c for c in dataframe.columns if c != 'Genes'] + ['Genes']
            dataframe = dataframe[cols]

        # store processed df
        self.dataframe = dataframe

        # Setup table shape
        self.table.setRowCount(len(dataframe))
        self.table.setColumnCount(len(dataframe.columns))
        self.table.setHorizontalHeaderLabels(
            [str(c) for c in dataframe.columns])

        # Fill cells with appropriate sortable items
        for r, row in enumerate(dataframe.itertuples(index=False)):
            for c, value in enumerate(row):
                col_name = dataframe.columns[c]
                item = None

                # normalize to str for safe operations below
                sval = "" if value is None else str(value)

                if col_name == "Genes":
                    gene_count = len(sval.split(";")) if sval else 0
                    item = self.NumericTableWidgetItem(gene_count, sval)

                elif col_name == "Overlap":
                    # "X/Y" -> float ratio for sorting
                    try:
                        num, denom = map(int, sval.split("/"))
                        frac = num / denom if denom else 0.0
                    except Exception:
                        frac = 0.0
                    item = self.NumericTableWidgetItem(frac, sval)

                elif col_name in {"P-value", "Adjusted P-value"}:
                    try:
                        numv = float(value)
                    except Exception:
                        numv = 0.0
                    item = self.NumericTableWidgetItem(
                        numv, self._format_number(numv, c))

                elif col_name in {"Odds Ratio", "Combined Score", "Z-Score"}:
                    try:
                        numv = float(value)
                    except Exception:
                        numv = 0.0
                    item = self.NumericTableWidgetItem(
                        numv, self._format_number(numv, c))

                elif col_name in {"Count", "Term Size"}:
                    try:
                        numv = int(value)
                    except Exception:
                        numv = 0
                    item = self.NumericTableWidgetItem(
                        numv, self._format_number(numv, c))

                else:
                    item = QTableWidgetItem(sval)

                # non-editable
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(r, c, item)

    def _filter_table(self) -> None:
        """Filter table rows based on search term and type."""
        if "Term" in self.search_type.currentText():
            self._filter_terms()
        else:
            self._filter_genes()

    def _filter_genes(self) -> None:
        """Filter table rows based on the search term for genes."""
        q = self.search_term.text().strip().lower()
        col = self._column_index("Genes")
        for row in range(self.table.rowCount()):
            genes_item = self.table.item(row, col) if col >= 0 else None
            match = q in genes_item.text().lower() if genes_item else False
            self.table.setRowHidden(row, not match)

    def _filter_terms(self) -> None:
        """Filter table rows based on the search term for terms."""
        q = self.search_term.text().strip().lower()
        col = self._column_index("Term")
        for row in range(self.table.rowCount()):
            term_item = self.table.item(row, col) if col >= 0 else None
            match = q in term_item.text().lower() if term_item else False
            self.table.setRowHidden(row, not match)

    def _column_index(self, name: str) -> int:
        """Get the column index for a given column name, or -1 if not found."""
        headers = [self.table.horizontalHeaderItem(
            i).text() for i in range(self.table.columnCount())]
        try:
            return headers.index(name)
        except ValueError:
            return -1

    def _toggle_column_visibility(self, column_index: int, is_visible: bool) -> None:
        """Toggle column visibility."""
        self.table.setColumnHidden(column_index, not is_visible)

    def _copy_to_clipboard(self) -> None:
        """Copy selected table items to the clipboard."""
        selected_items = self.table.selectedItems()
        if not selected_items:
            return
        grouped = {}
        for it in selected_items:
            grouped.setdefault(it.row(), []).append(it.text())
        text = "\n".join("\t".join(grouped[r]) for r in sorted(grouped))
        QApplication.clipboard().setText(text)

    def _save_results(self) -> None:
        """Save the current results to a file."""
        rows: list[list[str]] = self._get_marked_rows()
        if len(rows) == 1:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Results", "", "TSV Files (*.tsv)")
        if not file_path:  # User canceled
            return

        with open(file_path, "w", encoding="utf-8") as f:
            for row in rows:
                f.write("\t".join(row) + "\n")

        msg = QMessageBox(self)
        msg.setWindowTitle("Results Saved")
        msg.setText("The results have been saved to a file.")
        msg.setIcon(QMessageBox.Information)
        msg.exec_()

    def _get_marked_rows(self) -> list[list[str]]:
        """Get the currently marked rows in the table.

        Returns:
            list[list[str]]: List of rows, where each row is a list of cell contents.
        """
        out: list[list[str]] = []
        header = [self.table.horizontalHeaderItem(
            i).text() for i in range(self.table.columnCount())]

        out.append(header)
        # first add marked rows
        for r in range(self.table.rowCount()):
            if self.table.isRowHidden(r):
                continue
            it = self.table.item(r, 0)
            if it and it.checkState() == Qt.Checked:
                out.append([self.table.item(r, c).text()
                           for c in range(self.table.columnCount())])
        if len(out) > 1:  # more than just the header
            return out

        # else include all rows
        for r in range(self.table.rowCount()):
            out.append([self.table.item(r, c).text()
                       for c in range(self.table.columnCount())])

        return out

    def _adjust_number_precision(self) -> None:
        """Adjust numerical precision dynamically based on column width."""
        for c in range(self.table.columnCount()):
            header_item = self.table.horizontalHeaderItem(c)
            if not header_item:
                continue
            name = header_item.text()
            if name in {"P-value", "Adjusted P-value", "Odds Ratio", "Combined Score"}:
                for r in range(self.table.rowCount()):
                    it = self.table.item(r, c)
                    if isinstance(it, EnrichmentResultsWidget.NumericTableWidgetItem):
                        it.setText(self._format_number(it.value, c))

    def _format_number(self, value: float | int | str, col_idx: int) -> str:
        """Format numbers dynamically based on column width, 
        using scientific notation for small values.

        Args:
            value (float | int | str): The numeric value to format.
            col_idx (int): The column index for width reference.
        Returns:
            str: Formatted string representation of the number.
        """
        width = self.table.columnWidth(col_idx)
        # scientific for small values
        try:
            v = float(value)
        except Exception:
            return str(value)
        if v != 0 and abs(v) < 1e-3:
            return f"{v:.2e}"
        # integer formatting if it's an int
        if isinstance(value, int) or (isinstance(value, float) and v.is_integer()):
            return f"{int(v):d}"
        # dynamic rounding
        if width < 50:
            return f"{v:.1g}"
        else:
            return f"{v:.3f}"
