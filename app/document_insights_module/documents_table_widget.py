"""Provides the table widget for displaying documents in the document insights module"""

# --- Standard Library Imports ---
from typing import Any

# --- Third Party Imports ---
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

# --- Local Imports ---
from app.database.database_manager import DatabaseManager


# --- Public Classes ---
class DocumentsTableWidget(QWidget):
    """ Widget to display a table of documents from the database. """

    def __init__(self, db_path: str, main_app: Any, document_view: Any,
                 db_manager: DatabaseManager, web_view_callback: Any, stats_callback: Any):
        """ 
        Initialize the Documents Table Widget.

        Args:
            db_path (str): Path to the SQLite database.
            main_app (Any): Reference to the main application.
            document_view (Any): Reference to the parent document view.
            db_manager (DatabaseManager): Database manager instance.
            web_view_callback (Any): Callback function to update the web view.
            stats_callback (Any): Callback function to update statistics.
        """

        super().__init__()
        self.db_path = db_path
        self.main_app = main_app
        self.document_view = document_view

        self.db_manager = db_manager
        self.web_view_callback = web_view_callback
        self.stats_callback = stats_callback
        self.num_articles = self.db_manager.get_number_articles()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self.article_table = QTableWidget()
        self.article_table.setAlternatingRowColors(True)
        # Keeping the original column count
        self.article_table.setColumnCount(4)
        self.article_table.setHorizontalHeaderLabels(
            ["PMC ID", "PubMed ID", "Sections", "Title"])
        self.article_table.itemSelectionChanged.connect(
            self._on_article_selected)

        # Enable sorting
        self.article_table.setSortingEnabled(True)

        # Ensure the title column wraps text
        self.article_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.article_table.setWordWrap(True)  # Allow text wrapping in cells
        self.article_table.resizeRowsToContents()  # Adjust row height

        # Set fixed widths for first three columns
        self.article_table.setColumnWidth(0, 100)  # PMC ID
        self.article_table.setColumnWidth(1, 80)  # PubMed ID
        self.article_table.setColumnWidth(2, 80)  # Sections

        self.num_articles = self.db_manager.get_number_articles()

        # layout.addWidget(self.search_bar)  # Add search bar
        layout.addWidget(self.article_table)

        self.update_articles()
        self.setLayout(layout)

    # --- Public Methods ---
    def update_db_path(self, db_path: str) -> None:
        """ Update the database path and refresh the database manager. """
        self.db_path = db_path
        self.db_manager = DatabaseManager(self.db_path)
        self.document_view.db_manager = self.db_manager

    def update_articles(self) -> None:
        """ Fetch and display articles from the database. """
        query = "SELECT pmc_id, pubmed_id, title, authors, journal, year FROM articles"
        self.articles = self.db_manager.fetch_data(
            query)  # Store all articles for filtering

        # Fetch flat rows: [(pubmed_id, passage_text), ...]
        query = "SELECT pubmed_id, passage_text FROM passages"
        res_df = self.db_manager.fetch_data(query)

        self.passage_data = (
            res_df.dropna(subset=['pubmed_id', 'passage_text'])
            .groupby('pubmed_id', sort=False)['passage_text']
            .apply(list)
            .to_dict()
        )
        self._populate_table(self.articles)

        number_articles: int = self.db_manager.get_number_articles()
        self.document_view.label = QLabel(
            f"Database contains {number_articles} files")

    def filter_articles(self) -> None:
        """Filters the table based on search input."""
        search_text = self.document_view.search_bar.text().strip().lower()

        if not search_text:
            # Reset to full list if search is cleared
            self._populate_table(self.articles)
            return

        filtered_articles = self.articles[
            self.articles.apply(lambda row: search_text in str(row[0]).lower() or  # PMC ID
                                # PubMed ID
                                search_text in str(row[1]).lower() or
                                search_text in row[2].lower(),  # Title
                                axis=1)
        ]

        self._populate_table(filtered_articles)

    # --- Private Methods ---
    def _on_article_selected(self) -> None:
        """ Handles article selection from the table."""
        selected_row: int = self.article_table.currentRow()
        if selected_row >= 0:
            pmc_id: str = self.article_table.item(selected_row, 0).text()
            pubmed_id: str = self.article_table.item(selected_row, 1).text()
            self.web_view_callback(pubmed_id)
            self.stats_callback(pmc_id)

    def _populate_table(self, articles: Any) -> None:
        """
        Populates the table with article data.

        Args:
            articles (pd.DataFrame): The articles to display in the table.

        Returns:
            None
        """
        self.article_table.setRowCount(len(articles))
        # Disable sorting while populating data
        self.article_table.setSortingEnabled(False)

        for row, (pmc_id, pubmed_id, title, _, _, _) in enumerate(articles.values):
            if not str(pmc_id).startswith("PMC"):
                pmc_id = "None"
            self.article_table.setItem(row, 0, QTableWidgetItem(str(pmc_id)))
            self.article_table.setItem(
                row, 1, QTableWidgetItem(str(pubmed_id)))

            # Convert to int explicitly and set sorting type
            tmp_passages = self.passage_data.get(pubmed_id, [])
            # len(passage_data.get(pmc_id, []))
            passage_count = len(tmp_passages)
            passage_item = QTableWidgetItem()
            # Set numerical data for sorting
            passage_item.setData(Qt.EditRole, passage_count)
            self.article_table.setItem(row, 2, passage_item)

            title_item = QTableWidgetItem(title)
            title_item.setFlags(title_item.flags() & ~
                                Qt.ItemIsEditable)  # Make non-editable
            title_item.setToolTip(title)  # Show full title on hover
            self.article_table.setItem(row, 3, title_item)

        self.article_table.setSortingEnabled(
            True)  # Enable sorting after populating
        # Adjust row height to fit wrapped text
        self.article_table.resizeRowsToContents()
