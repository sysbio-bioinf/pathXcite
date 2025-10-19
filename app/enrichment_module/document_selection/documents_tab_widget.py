"""Provides the tab widget for document selection and statistics in the enrichment module"""

# --- Standard Library Imports ---
from typing import Any

# --- Third Party Imports ---
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QCheckBox, QLabel, QSplitter, QVBoxLayout, QWidget

# --- Local Imports ---
from app.database.database_analysis import analyze_pubmed_data
from app.database.database_query import (
    get_article_count,
    get_pubmed_ids_from_db,
    retrieve_document_data,
)
from app.enrichment_module.document_selection.document_box import DocumentBox
from app.enrichment_module.document_selection.stats_view_widget import StatsViewWidget
from app.report.create_report import generate_interactive_html_report
from app.utils import get_default_html_svg, resource_path

# --- Public Classes ---


class DocumentsTabWidget(QSplitter):
    """Tab widget for document selection and statistics view in the enrichment module."""

    def __init__(self, main_app: Any, gene_lists_view: Any, parent: Any = None):
        """
        Initialize the DocumentsTabWidget.
        It contains a document selection box and a statistics view.

        Args:
            main_app: The main application instance.
            gene_lists_view: The gene lists view instance to update based on document selection.
            parent: The parent widget.
        """
        super().__init__(parent)
        self.gene_lists_view = gene_lists_view
        self.main_app = main_app
        self.checked_pubmed_ids: set[str] = set()
        self.retrieved_document_data_dict: dict[str, Any] = {}
        self.current_doc_set_stats: str = ""
        self.db_path: str = ""
        self.num_articles: int = 0
        self.show_documents_without_genes: bool = False
        self.pubmed_ids: list[str] = []

        self._bulk_updating = False  # to suppress intermediate signals during bulk updates
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        # Select All Documents checkbox
        self.select_all_documents_checkbox = QCheckBox("Select All Documents")
        self.select_all_documents_checkbox.stateChanged.connect(
            self._toggle_select_all_documents)
        self.select_all_documents_checkbox.setFixedHeight(30)
        left_layout.addWidget(self.select_all_documents_checkbox)

        self.document_header_label = QLabel("Document Data")
        self.document_header_label.setObjectName("documentsHeader")
        left_layout.addWidget(self.document_header_label)

        self.document_box = DocumentBox()
        self.document_box.toggle_select_all.hide()

        # Wire selection changes from cards to our legacy selection set + gene list updates.
        self.document_box.selectionChanged.connect(
            self._on_card_selection_changed)
        left_layout.addWidget(self.document_box)

        self.addWidget(left_panel)

        self.stats_main_view = StatsViewWidget(self.main_app)
        self.addWidget(self.stats_main_view)

    def update_document_list(self) -> None:
        """ Updates the document list when a new database is selected or settings change. """
        self.db_path = self.main_app.get_current_database()
        self.gene_lists_view.db_path = self.db_path
        self.num_articles = get_article_count(self.db_path)

        # check if Show documents without genes checkbox is checked or not
        self.show_documents_without_genes = False

        # if documents without genes shouldnt be shown (checkbox is unchecked) the number of
        # articles shown in the header label should be the number of articles with genes
        tmp_num_articles = self.num_articles
        if not self.show_documents_without_genes:
            tmp_num_articles = 0
            for _, value in self.retrieved_document_data_dict.items():
                if value.get("num_genes", 0) > 0:
                    tmp_num_articles += 1

        # Retrieve PubMed IDs from the database
        self.pubmed_ids = get_pubmed_ids_from_db(self.db_path)

        articles_for_box: list[dict] = []
        for pubmed_id in self.pubmed_ids:
            document_data = retrieve_document_data(pubmed_id, self.db_path)
            num_genes = len(document_data.get("annotations", {}))
            self.retrieved_document_data_dict[pubmed_id] = {'document_data': document_data,
                                                            'num_genes': num_genes}

            # Filter based on checkbox state
            if num_genes == 0 and not self.show_documents_without_genes:
                continue  # Skip documents without genes if the option is disabled

            a = dict(document_data)
            # ensure pubmed_id present (some call paths rely on it)
            a['pubmed_id'] = pubmed_id
            articles_for_box.append(a)

        self.document_box.update_documents(articles_for_box)

        # sort the tree widget items by the number of genes of each document
        header_text = f"Document Data ({tmp_num_articles} articles)"

        self.document_header_label.setText(header_text)

        self._clear_checked_pubmed_ids()  # Reset checked PubMed IDs
        self.gene_lists_view.update_gene_list_tab()

    # --- Public Methods ---
    def get_checked_pubmed_ids(self) -> set[str]:
        """Returns the set of checked PubMed IDs."""
        return self.checked_pubmed_ids

    def update_stats_tab(self) -> None:
        """
        Updates the content of the statistics tab based on the currently selected documents.
        """
        selected_documents: list[dict] = []
        for pubmed_id in self.get_checked_pubmed_ids():
            document_data = self.retrieved_document_data_dict.get(
                pubmed_id, {}).get("document_data", {})
            if document_data:
                document_data['annotations'] = self._reformate_annotations_for_export(
                    document_data['annotations'])
                selected_documents.append(document_data)

        selected_pubmed_ids = [doc.get('pubmed_id')
                               for doc in selected_documents]

        if selected_pubmed_ids:
            other_version = analyze_pubmed_data(
                selected_documents, selected_pubmed_ids)
            self.current_doc_set_stats = generate_interactive_html_report(
                other_version
            )
            self.stats_main_view.set_stats_html(self.current_doc_set_stats)
        else:
            self.stats_main_view.set_stats_html(
                get_default_html_svg(str(resource_path("assets/icons/stats.svg")),
                                     "Please select documents to view statistics.")
            )

        header_text = f"Document Data ({len(selected_pubmed_ids)} articles)"
        self.document_header_label.setText(header_text)

    # --- Private Methods ---
    def _on_card_selection_changed(self, pubmed_id: str, checked: bool) -> None:
        """Handle selection changes from individual document cards."""
        # Keep the selection set in sync for both single and bulk changes
        if checked:
            self.checked_pubmed_ids.add(pubmed_id)
        else:
            self.checked_pubmed_ids.discard(pubmed_id)

        # Skip heavy updates while doing a bulk toggle
        if not self._bulk_updating:
            self.gene_lists_view.update_gene_list_tab()

    def _toggle_select_all_documents(self, state) -> None:
        """(Un)selects all documents based on the state, updates the gene list once."""
        check = state == Qt.Checked

        # During bulk, let slot update set per-item but don't recompute the gene list each time
        self._bulk_updating = True
        try:
            self.checked_pubmed_ids.clear()
            # This will emit selectionChanged per card; the slot will run but skip the heavy update.
            self.document_box.set_all_checked(check)
        finally:
            self._bulk_updating = False

        # Now do a single gene list update for the bulk change
        self.gene_lists_view.update_gene_list_tab()

    def _clear_checked_pubmed_ids(self) -> None:
        """Clears the set of checked PubMed IDs."""
        self.checked_pubmed_ids.clear()

    def _reformate_annotations_for_export(self, annotations: dict) -> dict:
        """ 
        Reformat annotations for export.

        Args:
            annotations: A dictionary with keys as tuples (entrez_id, gene_symbol, tax_id)
                         and values as annotation data.

        Returns:
            A reformatted dictionary with entrez_id as keys and a nested dictionary containing
            gene_symbol, tax_id, and annotations as values.
        """
        reformatted_annotations: dict = {}
        for key_tuple, value in annotations.items():
            entrez_id = key_tuple[0]
            gene_symbol = key_tuple[1]
            tax_id = key_tuple[2]
            annotations_data = value
            reformatted_annotations[entrez_id] = {
                "gene_symbol": gene_symbol,
                "tax_id": tax_id,
                "annotations": annotations_data
            }
        return reformatted_annotations

    '''def handle_checkbox_change(self, item, column): # TODO Check usage
        """Ensure only checkbox changes are detected."""
        return'''
