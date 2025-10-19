"""Provides the statistics view widget for document selection in the enrichment module"""

# --- Third Party Imports ---
from PyQt5.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QMenu,
    QMenuBar,
    QMessageBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

# --- Local Imports ---
from app.util_widgets.svg_button import SvgHoverButton
from app.utils import get_default_html_svg, resource_path


# --- Public Classes ---
class StatsViewWidget(QWidget):
    """Widget for displaying document selection statistics in the enrichment module."""
    PAGE_INIT = 0
    PAGE_STATS = 1

    def __init__(self, main_app):
        """Initialize the StatsViewWidget.
        It contains a stacked widget with an initial info page and a statistics HTML page.

        Args:
            main_app: The main application instance.
        """
        super().__init__()
        self.main_app = main_app
        self.html: str | None = None

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
            "Please select a document to view its genes or adjust the filters."
        )

        self.init_page.setHtml(html)
        self.stacked_widget.addWidget(self.init_page)  # index 0

        # ----- Page 1: Table view page
        self.stats_html_page = QWidget()
        stats_html_layout = QVBoxLayout(self.stats_html_page)

        # Toolbar
        self.menu_bar = QMenuBar()
        self.menu = QMenu("Actions", self)
        self.menu_bar.addMenu(self.menu)
        stats_html_layout.addWidget(self.menu_bar)

        self.export_stats_btn = SvgHoverButton(
            base_name="export",
            tooltip="Export Statistics to HTML",
            triggered_func=lambda: self.export_stats(),
            size=20,
            parent=self
        )

        term_toolbar = QWidget()
        term_toolbar_layout = QHBoxLayout(term_toolbar)
        term_toolbar_layout.setContentsMargins(0, 0, 0, 0)
        term_toolbar_layout.setSpacing(5)
        term_toolbar_layout.addStretch()
        term_toolbar_layout.addWidget(self.export_stats_btn)

        stats_html_layout.addWidget(term_toolbar)

        # Table
        self.stats_page = self.main_app.get_new_web_view(parent=self)
        html = get_default_html_svg(
            str(resource_path("assets/icons/lightbulb.svg")),
            "Please start enrichment process to get insights into enriched pathways."
        )

        stats_html_layout.addWidget(self.stats_page)

        # stats html page should expand vertically
        stats_html_layout.setStretchFactor(self.stats_page, 1)

        self.stacked_widget.addWidget(self.stats_html_page)  # index 1

        message = "Please select a document to view its genes or adjust the filters."
        self.set_stats_html(get_default_html_svg(str(resource_path("assets/icons/lightbulb.svg")),
                                                 message))

    def export_stats(self) -> None:
        """Export the current statistics HTML to a file."""
        # get html of the stats tab
        stats_html = self.html

        if stats_html is None:
            QMessageBox.critical(
                self, "Error", "Please select documents before exporting.")
            return

        # ask the user if they want to export the results
        message = "Do you want to export the document set statistics? (Saves a *.html file)"
        export = QMessageBox.question(self, "Export Results",
                                      message,
                                      QMessageBox.Yes | QMessageBox.No)

        if export == QMessageBox.Yes:
            # get the file name and location to save the file
            file_path, _ = QFileDialog.getSaveFileName(self, "Save File", "",
                                                       "HTML Files (*.html);")

            if file_path:
                if not file_path.endswith(".html"):
                    file_path += ".html"
                if file_path.endswith(".html"):
                    # save the results as an html file
                    with open(file_path, "w", encoding='utf-8') as file:
                        file.write(stats_html)
        else:
            return

    # --- Public Methods ---
    def set_stats_html(self, html: str | None) -> None:
        """Set the statistics HTML content and update the view.
        Args:
            html: The HTML content to display. If None, the initial page is shown.
        """

        self.html = html
        self.stats_page.setHtml(self.html)
        # swap stacked page
        self._update_view_state()

    def _update_html(self, message: str) -> None:  # TODO Check usage
        """Update the initial HTML page with a custom message.

        Args:
            message: The message to display on the initial page.
        """
        icon_path = str(resource_path("assets/icons/lightbulb.svg"))
        self.init_page.setHtml(get_default_html_svg(icon_path, message))

    # --- Private Methods ---
    def _has_data(self) -> bool:
        """Check if there is statistics HTML data to display."""
        return self.html is not None

    def _update_view_state(self) -> None:
        """Update the stacked widget view based on data availability."""
        self.stacked_widget.setCurrentIndex(
            self.PAGE_STATS if self._has_data() else self.PAGE_INIT)

    def save_results(self) -> None:  # TODO Check usage
        """Save the current results to a file."""
        '''rows = self.get_marked_rows()
        if len(rows) == 1:
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Results", "", "TSV Files (*.tsv)")
        if not file_path:
            return
        with open(file_path, "w", encoding="utf-8") as f:
            for row in rows:
                f.write("\t".join(row) + "\n")
        msg = QMessageBox(self)
        msg.setWindowTitle("Results Saved")
        msg.setText("The results have been saved to a file.")
        msg.setIcon(QMessageBox.Information)
        msg.exec_()'''
        pass
