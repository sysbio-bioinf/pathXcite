"""A widget for managing article IDs in the browser module holding a tree view of article IDs"""

# --- Standard Library Imports ---
import re
from typing import Any

# --- Third Party Imports ---
from PyQt5.QtWidgets import (
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

# --- Local Imports ---
from app.browser_module.article_id_tree import ArticleIdTreeWidget
from app.util_widgets.separator import get_separator

# --- Constants ---
# Regex patterns for ID validation
PMCID_RE = re.compile(r"^pmc\d+$", re.IGNORECASE)

# --- Public Classes ---


class ArticleIdWidget(QWidget):
    """
    Widget to manage and display article IDs (PubMed and PMC) in a tree view,
    with functionality to add custom IDs.

    Args:
        main_app: Main application instance for interaction.
        article_ids (dict[str, list[str]]): Initial article IDs with keys 'pmids' and 'pmcids'.
        saved_ids (list[str], optional): List of article IDs already saved in the database.
    """

    def __init__(self, main_app: Any, article_ids: dict[str, list[str]],
                 saved_ids: list[str] | None = None):
        super().__init__()
        self.main_app = main_app
        layout = QVBoxLayout(self)

        self._pending_selection_state: dict[str, bool] = {}
        self.db_path: str = ""
        self.pubmed_ids: list[str] = []
        self.pmc_ids: list[str] = []
        self.saved_ids: list[str] = saved_ids or []
        self.scan_behavior: str = "append"
        self.last_scan_msg: str = ""

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        layout.addWidget(self.scroll)

        self.article_tree = ArticleIdTreeWidget(
            self.main_app,
            article_ids.get("pmids", []),
            article_ids.get("pmcids", []),
            saved_ids
        )
        self.scroll.setWidget(self.article_tree)

        # --- Custom input row ---
        self.custom_add = QWidget()
        self.custom_add.setFixedHeight(150)
        self.custom_add_layout = QVBoxLayout(self.custom_add)
        self.custom_add_layout.setContentsMargins(0, 0, 0, 0)
        self.custom_add_layout.setSpacing(6)

        tmp_label = QLabel("<b>Add Custom IDs (comma-separated):</b>")
        self.custom_add_layout.addWidget(tmp_label)

        self.input_edit = QTextEdit()
        self.input_edit.setPlaceholderText(
            "Allowed: digits (PMID) or PMC1234567")
        self.input_edit.setFixedHeight(100)
        self.custom_add_layout.addWidget(self.input_edit)

        self.add_btn = QPushButton("Add IDs to List")
        self.add_btn.clicked.connect(self._on_add_ids_clicked)
        self.custom_add_layout.addWidget(self.add_btn)

        layout.addWidget(get_separator("horizontal"))
        layout.addWidget(self.custom_add)


    # --- Public Methods ---
    def update_articles(self, article_ids: dict[str, list[str]],
                        scan_behavior: str, saved_ids: list[str] | None = None) -> None:
        """
        Update the article IDs in the tree view based on the provided IDs and scan behavior.

        Args:
            article_ids (dict[str, list[str]]): Dictionary with keys 'pmids' and 'pmcids'
                containing lists of article IDs.
            scan_behavior (str): Behavior for updating IDs ('append' or 'replace').
            saved_ids (list[str] | None): Optional list of saved article IDs in the database.

        Returns:
            None
        """
        self.article_tree.update_article_ids(
            article_ids, scan_behavior, saved_ids=saved_ids)
        self.article_tree.update_saved_icons()


    # --- Private Methods ---
    def _notify_summary(self, summary: dict[str, list[str]]) -> None:
        """
        Notify the user about the result of adding custom IDs.
        Args:
            summary (dict): Summary of the addition process with keys:
                - 'added_pmids': list of added PubMed IDs
                - 'added_pmcids': list of added PMC IDs
                - 'duplicates': list of duplicate IDs skipped
                - 'invalid': list of invalid format IDs
        """
        added_pm = len(summary["added_pmids"])
        added_pc = len(summary["added_pmcids"])
        dups: list[str] = summary["duplicates"]
        bad: list[str] = summary["invalid"]

        messages: list[str] = []
        if added_pm or added_pc:
            pieces: list[str] = []
            if added_pm:
                pieces.append(f"Added {added_pm} PMID(s)")
            if added_pc:
                pieces.append(f"Added {added_pc} PMCID(s)")
            messages.append(" and ".join(pieces))
        if dups:
            messages.append(f"Skipped duplicates: {', '.join(dups)}")
        if bad:
            messages.append(f"Invalid format: {', '.join(bad)}\n"
                            f"   (Use digits for PMID, or PMC + digits for PMCID)")
        if not messages:
            messages.append("No changes.")

        QMessageBox.information(self, "Custom ID Upload", "\n".join(messages))

    def _on_add_ids_clicked(self) -> None:
        """Handle the addition of custom IDs."""
        raw = self.input_edit.toPlainText().strip()
        if not raw:
            QMessageBox.warning(
                self, "No Input", "Please enter at least one ID.")
            return
        summary: dict[str, list[str]
                      ] = self.article_tree.add_custom_ids_text(raw)
        self.input_edit.clear()
        self._notify_summary(summary)

    