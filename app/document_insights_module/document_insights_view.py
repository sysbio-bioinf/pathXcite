"""Provides the UI elements for the document insights module"""

# --- Standard Library Imports ---
from typing import Any

# --- Third Party Imports ---
from PyQt5.QtCore import QUrl
from PyQt5.QtWidgets import (
    QLabel,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)

# --- Local Imports ---
from app.database.database_manager import DatabaseManager
from app.document_insights_module.document_stats_creation import generate_html
from app.document_insights_module.documents_table_widget import DocumentsTableWidget
from app.util_widgets.icon_line_edit import IconLineEdit
from app.utils import get_default_html_svg, resource_path

PUBMED_BASE_URL = "https://pubmed.ncbi.nlm.nih.gov/"
PUBTATOR_BASE_URL = "https://www.ncbi.nlm.nih.gov/research/pubtator3/publication/"
# --- Public Classes ---


class DocumentInsightsView(QSplitter):
    """Provides a UI for exploring and analyzing documents in the database."""

    def __init__(self, main_app: Any, db_path: str = None):
        """
        Initialize the Document Insights View.

        Args:
            main_app (Any): Reference to the main application.
            db_path (str, optional): Path to the SQLite database. Defaults to None.
        """
        super().__init__()
        self.table_widget = None
        self.main_app = main_app
        self.loaded_once = False

        self.pmc_id: str | None = None
        self.pubmed_id: str | None = None

        # Main layout
        self.main_widget = QWidget()
        self.main_layout = QVBoxLayout(self.main_widget)

        # Stacked Widget to switch between views
        self.stack = QStackedWidget()
        self.main_layout.addWidget(self.stack)

        self.db_path: str = db_path

        # View 2: Main document view
        self.document_view = QWidget()
        doc_layout = QVBoxLayout(self.document_view)
        # Remove margins for a cleaner look
        doc_layout.setContentsMargins(0, 0, 0, 0)

        self.db_manager = DatabaseManager(db_path)

        # Left Side: Table View
        self.toolbar_actions: list[QWidgetAction] = []
        self.toolbar_actions2: list[QWidgetAction] = []

        # Right Side: Tabbed Web View
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(
            QTabWidget.North)  # Tabs on the left side
        self.tab_widget.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Create WebEngineViews for PubTator & PubMed
        self.pubtator_view = self.main_app.get_new_web_view(
            parent=self.main_app)
        self.pubmed_view = self.main_app.get_new_web_view(parent=self.main_app)

        # Statistics Tab (contains multiple WebEngineViews)
        self.stats_view = QTabWidget()

        self.stats_view_html_section_plot = self.main_app.get_new_web_view()  # parent=self)

        self.table_widget = DocumentsTableWidget(self.db_path, self.main_app,
                                                 self, self.db_manager, self._update_web_views,
                                                 self._update_statistics)
        doc_layout.addWidget(self.table_widget)

        # View 1: Placeholder if no database is set
        if not self.db_path:
            self.notification_widget = QWidget()
            notification_layout = QVBoxLayout(self.notification_widget)
            notification_label = QLabel(
                "Please create a database first in the browser view.")
            notification_layout.addWidget(notification_label)
            self.stack.addWidget(self.notification_widget)  # Add to stack
            # return

        else:
            self.pubtator_view.setHtml(get_default_html_svg(
                icon_abs_path=str(resource_path(
                    "assets/icons/doc_search.svg")),
                message="Please select an article to view the PubTator website entry."))
            self.pubmed_view.setHtml(get_default_html_svg(
                icon_abs_path=str(resource_path(
                    "assets/icons/doc_search.svg")),
                message="Please select an article to view the PubMed website entry."))

            # Set default HTML content
            self.stats_view_html_section_plot.setHtml(get_default_html_svg(
                icon_abs_path=str(resource_path("assets/icons/stats.svg")),
                message="Please select an annotated PMC article to view statistics."))

            # Add tabs to main tab widget
            self.tab_widget.addTab(self.pubtator_view, "PubTator")
            self.tab_widget.addTab(self.pubmed_view, "PubMed")
            self.tab_widget.addTab(
                self.stats_view_html_section_plot, "Statistics")

            self.stack.addWidget(self.document_view)

        self._init_toolbar_actions()

        self.addWidget(self.main_widget)
        self.addWidget(self.tab_widget)

        self.setStretchFactor(0, 2)
        self.setStretchFactor(1, 1)

    # --- Private Methods ---
    def _init_toolbar_actions(self) -> None:
        """Initialize toolbar actions including the search bar and labels."""
        # Search bar for filtering articles
        self.label = QLabel(
            f"Database contains {self.db_manager.get_number_articles()} files")

        search_bar_tooltip = "Search for PMC ID, PubMed ID, or Title"
        self.search_bar = IconLineEdit("search", tooltip=search_bar_tooltip,
                                       on_click=None,
                                       on_text_changed=self.table_widget.filter_articles,
                                       on_return=None, icon_size=22,
                                       icon_position="right")
        self.search_bar.setPlaceholderText(
            "Search for PMC ID, PubMed ID, or Title...")
        self.search_bar.setFixedHeight(30)
        self.search_bar.setMinimumWidth(400)

        # Wrap each widget in a QWidgetAction so TopBar can render them
        def wrap(widget):
            act = QWidgetAction(self)      # parent = page (WebBrowser)
            # toolbar will merely show it, not own it
            act.setDefaultWidget(widget)
            return act

        self.toolbar_actions.extend([
            wrap(self.label)
        ])

        self.toolbar_actions2.extend([wrap(self.search_bar)])

    def _update_web_views(self, pubmed_id: str | None = None) -> None:
        """ 
        Update the WebEngineViews with the correct PubTator and PubMed pages 

        Args:
            pubmed_id (str | None): The PubMed ID of the selected article.

        Returns:
            None
        """
        if pubmed_id:
            pubtator_url = f"{PUBTATOR_BASE_URL}{pubmed_id}"
            pubmed_url = f"{PUBMED_BASE_URL}{pubmed_id}"
            self.pubtator_view.setUrl(QUrl(pubtator_url))
            self.pubmed_view.setUrl(QUrl(pubmed_url))

    def _update_statistics(self, pmc_id: str | None = None, pubmed_id: str | None = None) -> None:
        """ 
        Update the statistics view with the correct article statistics

        Args:
            pmc_id (str | None): The PMC ID of the selected article.
            pubmed_id (str | None): The PubMed ID of the selected article.

        Returns:
            None
        """
        if pmc_id is not None:
            self.pmc_id = pmc_id

        if self.pmc_id and self.pmc_id is not None:
            section_chart_html = generate_html(self.db_manager, self.pmc_id)
            self.stats_view_html_section_plot.setHtml(section_chart_html)

        self.tab_widget.setCurrentIndex(2)

        if not self.loaded_once:
            self.stats_view.setCurrentIndex(1)
            self.stats_view.setCurrentIndex(2)
            self.stats_view.setCurrentIndex(3)
            self.loaded_once = True
