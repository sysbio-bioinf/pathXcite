"""This module provides a tree widget for displaying and managing article IDs."""

# --- Standard Library Imports ---
import re
from typing import Any

# --- Third Party Imports ---
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

# --- Local Imports ---
from app.util_widgets.svg_button import DatabaseStatusButton, SvgButton

# --- Constants ---
# Regex patterns for ID validation
PMCID_RE = re.compile(r"^pmc\d+$", re.IGNORECASE)

# --- Public Classes ---


class ArticleIdTreeWidget(QWidget):
    """
    Widget to display and manage article IDs (PubMed and PMC) in a tree view.

    Args:
        main_app: Main application instance for interaction.
        pubmed_ids (list[str], optional): Initial list of PubMed IDs.
        pmc_ids (list[str], optional): Initial list of PMC IDs.
        saved_ids (list[str], optional): List of article IDs already saved in the database.
    """

    def __init__(self, main_app: Any,
                 pubmed_ids: list[str] | None = None,
                 pmc_ids: list[str] | None = None,
                 saved_ids: list[str] | None = None):

        super().__init__()

        self._pending_selection_state: dict[str, bool] = {}
        self.last_scan_msg: str = ""
        self.scan_behavior: str = "append"  # or "replace"
        self.current_db_ids: set[str] = set()
        self.main_app: Any = main_app
        self.db_path: str = main_app.get_current_database()
        self.saved_ids: list[str] = saved_ids or []
        self.pubmed_ids: list[str] = pubmed_ids or []
        self.pmc_ids: list[str] = pmc_ids or []

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(QLabel("<b>Detected Article IDs (Web):</b>"))
        self.label = QLabel()
        layout.addWidget(self.label)

        self.add_all_ids_to_db_button = QPushButton("Add Selected to DB")
        self.add_all_ids_to_db_button.clicked.connect(self._add_selected_to_db)

        # Tree widget
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.tree)
        layout.addWidget(self.add_all_ids_to_db_button)

        self._build_tree()


    # --- Public Methods ---
    def update_article_ids(self, article_ids: dict[str, list[str]],
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

        self.db_path: str = self.main_app.get_current_database()

        new_pmids: list[str] = self._normalize_ids(
            list(article_ids.get("pmids", [])))
        new_pmcids: list[str] = self._normalize_ids(
            list(article_ids.get("pmcids", [])))

        # Ensure we have current lists
        self.pubmed_ids = list(getattr(self, "pubmed_ids", []))
        self.pmc_ids = list(getattr(self, "pmc_ids", []))

        behavior = self._normalize_behavior(scan_behavior)

        # Remember what the user had checked
        prev_sel = self._capture_selection_state()

        dupes_pm = dupes_pmc = 0
        if behavior == "replace":
            self.pubmed_ids = new_pmids
            self.pmc_ids = new_pmcids
            self.last_scan_msg = f"Replaced with {len(new_pmids) + len(new_pmcids)}"
            # When replacing, keep selection only for IDs that still exist
            kept_sel = {k: v for k, v in prev_sel.items()
                        if k in set(new_pmids) or k in set(new_pmcids)}
            self._set_pending_selection_state(kept_sel)
        else:
            # append with stable dedupe
            stable_merge = self._stable_merge(self.pubmed_ids, new_pmids)
            self.pubmed_ids: list[str] = stable_merge[0]
            dupes_pm: int = stable_merge[1]
            stable_merge = self._stable_merge(self.pmc_ids, new_pmcids)
            self.pmc_ids: list[str] = stable_merge[0]
            dupes_pmc: int = stable_merge[1]

            added = (len(new_pmids) + len(new_pmcids)) - (dupes_pm + dupes_pmc)
            skipped: int = dupes_pm + dupes_pmc

            if skipped:
                self.last_scan_msg = f"Appended {added}, {skipped} duplicates skipped"
            else:
                self.last_scan_msg = f"Appended {added}"
            # When appending, keep all previous selections; new ones start unchecked
            self._set_pending_selection_state(prev_sel)

        if saved_ids is not None:
            self.saved_ids: list[str] = saved_ids

        self.scan_behavior: str = behavior  # normalized
        self._build_tree()
        # Clear the one-time selection state
        self._set_pending_selection_state({})

    def update_saved_icons(self) -> None:
        """
        Update the database status icons for each article ID in the tree view 
        based on their presence in the current database.

        Args:
            None

        Returns:
            None
        """
        self.db_path: str = self.main_app.get_current_database()
        self.current_db_ids: dict[str, list[str]] = self.main_app.get_db_ids()
        current_db_pmids: list[str] = self.current_db_ids.get("pmids", [])
        current_db_pmcids: list[str] = self.current_db_ids.get("pmcids", [])
        for i in range(self.tree.topLevelItemCount()):
            top_item: QTreeWidgetItem = self.tree.topLevelItem(i)
            for j in range(top_item.childCount()):
                child_item: QTreeWidgetItem = top_item.child(j)
                article_id: str = child_item.data(0, Qt.UserRole)
                row_widget: QWidget = self.tree.itemWidget(child_item, 0)
                if not row_widget:
                    continue

                # Find the DB button in row layout
                for k in range(row_widget.layout().count()):
                    widget: DatabaseStatusButton = row_widget.layout().itemAt(k).widget()
                    if isinstance(widget, DatabaseStatusButton):
                        is_saved = article_id in current_db_pmids or article_id in current_db_pmcids
                        widget.update_icon(is_saved)
                        break


    # --- Private Methods ---
    def add_custom_ids_text(self, raw_text: str) -> dict:
        """
        Parse a comma-separated string of IDs, validate, and merge into pubmed_ids / pmc_ids.
        Returns a summary dict for user notification.
        Allowed formats:
        - PMIDs: digits only (e.g., '12345678')
        - PMCIDs: 'PMC' or 'pmc' followed by digits (e.g., 'PMC1234567')

        Args:
            raw_text (str): Comma-separated string of article IDs.

        Returns:
            dict: Summary with keys 'added_pmids', 'added_pmcids', 'duplicates', 'invalid'.
        """
        parts = [p.strip().upper()
                 for p in (raw_text or "").split(",") if p.strip()]
        if not parts:
            return {"added_pmids": [], "added_pmcids": [], "duplicates": [], "invalid": []}

        # work with lowercase sets only for duplicate detection
        pm_lower = {x.lower() for x in self.pubmed_ids}
        pc_lower = {x.lower() for x in self.pmc_ids}

        added_pmids: list[str] = []
        added_pmcids: list[str] = []
        duplicates: list[str] = []
        invalid: list[str] = []

        for tok in parts:
            low = tok.lower()
            if self._is_valid_pmid(tok):
                if low in pm_lower:
                    duplicates.append(tok)
                else:
                    self.pubmed_ids.append(tok)
                    pm_lower.add(low)
                    added_pmids.append(tok)
            elif self._is_valid_pmcid(tok):
                if low in pc_lower:
                    duplicates.append(tok)
                else:
                    self.pmc_ids.append(tok)
                    pc_lower.add(low)
                    added_pmcids.append(tok)
            else:
                invalid.append(tok)

        # Rebuild tree to reflect changes
        if added_pmids or added_pmcids:
            self._build_tree()
            self.update_saved_icons()

        return {
            "added_pmids": added_pmids,
            "added_pmcids": added_pmcids,
            "duplicates": duplicates,
            "invalid": invalid,
        }

    def _build_tree(self) -> None:
        """Construct the tree view of article IDs.
        1. Clear existing items.
        2. Add PubMed and PMC categories with their IDs.
        3. Update the label with the total count of IDs.

        Args:
            None

        Returns:
            None
        """
        self.tree.blockSignals(True)
        # Safely disconnect existing handlers
        try:
            # clear any old handlers once per rebuild
            self.tree.itemChanged.disconnect()
        except TypeError:
            pass
        except RuntimeError as e:
            print(f"RuntimeError during disconnect: {e}")
        try:
            self.tree.clear()
            total = len(self.pubmed_ids) + len(self.pmc_ids)
            self.label.setText(f"  Found {total} Article IDs")

            self._add_category("PubMed", self.pubmed_ids, self.saved_ids)
            self._add_category("PMC", self.pmc_ids, self.saved_ids)
        finally:
            self.tree.blockSignals(False)

    def _add_category(self, name: str, ids: list[str], saved_ids: list[str] | None = None) -> None:
        """
        Add a category to the tree view.

        Args:
            name (str): The name of the category (e.g., "PubMed", "PMC").
            ids (list[str]): List of article IDs for this category.
            saved_ids (list[str] | None): List of IDs already saved in the database.

        Returns:
            None
        """
        ids: list[str] = self._normalize_list(ids)

        top_item = QTreeWidgetItem([f"{len(ids)} {name} IDs"])

        top_item.setFlags(top_item.flags() | Qt.ItemIsUserCheckable)
        top_item.setCheckState(0, Qt.Unchecked)
        self.tree.addTopLevelItem(top_item)

        toggle_btn = SvgButton(
            svg_file_name="find_on_page2.svg",
            tooltip="Expand/Collapse",
            triggered_func=lambda: top_item.setExpanded(
                not top_item.isExpanded()),
            size=16
        )
        self.tree.setItemWidget(top_item, 1, toggle_btn)
        top_item.setExpanded(True)

        def on_top_check_changed(state):
            """ When the top-level checkbox is changed, update all child checkboxes. """
            for i in range(top_item.childCount()):
                child_item: QTreeWidgetItem = top_item.child(i)
                widget: QWidget = self.tree.itemWidget(child_item, 0)
                if widget:
                    widget.checkbox.setChecked(state == Qt.Checked)

        self.tree.itemChanged.connect(
            lambda item, _: on_top_check_changed(
                item.checkState(0)) if item == top_item else None
        )

        saved_l = {s.lower() for s in (saved_ids or [])}

        for article_id in ids:
            item = QTreeWidgetItem()
            # Store article ID in item
            item.setData(0, Qt.UserRole, article_id)
            top_item.addChild(item)

            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(6)

            checkbox = QCheckBox()
            row_layout.addWidget(checkbox)

            is_saved = article_id.lower() in saved_l

            def on_db_click(aid=article_id):
                if aid not in self.saved_ids:
                    pass

            db_btn = DatabaseStatusButton(
                available=is_saved,
                tooltip="In DB" if is_saved else "Click to add to DB",
                triggered_func=on_db_click,
                size=16
            )
            db_btn.setEnabled(not is_saved)
            row_layout.addWidget(db_btn)

            open_btn = SvgButton(
                svg_file_name="open_in_browser.svg",
                tooltip=f"Open {article_id}",
                triggered_func=lambda _, aid=article_id,
                db_name=name: self._open_article_in_browser(aid, db_name),
                size=16
            )
            row_layout.addWidget(open_btn)

            id_label = QLabel(article_id)
            id_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            row_layout.addWidget(id_label)

            row_layout.addStretch()
            row_widget.setLayout(row_layout)

            row_widget.checkbox = checkbox
            self.tree.setItemWidget(item, 0, row_widget)

    def _get_selected_pmids(self) -> list[str]:
        """
        Get a list of selected PubMed IDs from the tree view.

        Args:
            None

        Returns:
            list[str]: List of selected PubMed IDs.
        """
        selected_pmids: list[str] = []
        for i in range(self.tree.topLevelItemCount()):
            top_item: QTreeWidgetItem = self.tree.topLevelItem(i)
            if "PubMed" in top_item.text(0):  # Check for PubMed
                for j in range(top_item.childCount()):
                    child_item: QTreeWidgetItem = top_item.child(j)
                    row_widget: QWidget = self.tree.itemWidget(child_item, 0)
                    if row_widget and row_widget.checkbox.isChecked():
                        selected_pmids.append(child_item.data(0, Qt.UserRole))
        return selected_pmids

    def _get_selected_pmcids(self) -> list[str]:
        """
        Get a list of selected PMC IDs from the tree view.

        Args:
            None

        Returns:
            list[str]: List of selected PMC IDs.
        """
        selected_pmcids: list[str] = []
        for i in range(self.tree.topLevelItemCount()):
            top_item = self.tree.topLevelItem(i)
            if "PMC" in top_item.text(0):
                for j in range(top_item.childCount()):
                    child_item: QTreeWidgetItem = top_item.child(j)
                    row_widget: QWidget = self.tree.itemWidget(child_item, 0)
                    if row_widget and row_widget.checkbox.isChecked():
                        selected_pmcids.append(child_item.data(0, Qt.UserRole))
        return selected_pmcids

    def _add_selected_to_db(self) -> None:
        """
        Add selected article IDs to the database.

        Args:
            None

        Returns:
            None
        """
        selected_pmids: list[str] = self._get_selected_pmids()
        selected_pmcids: list[str] = self._get_selected_pmcids()

        self.main_app.add_ids_to_database({
            "pmids": selected_pmids,
            "pmcids": selected_pmcids
        })

        self.update_saved_icons()

    def _open_article_in_browser(self, article_id: str, name: str) -> None:
        """
        Open the article information in the web browser.

        Args:
            article_id (str): The article ID to open.
            name (str): The database name ("PubMed" or "PMC").

        Returns:
            None
        """
        self.main_app.open_article_info(article_id, name)

    def _normalize_behavior(self, scan_behavior: str) -> str:
        """ Normalize scan behavior string to 'append' or 'replace'. """
        txt = (scan_behavior or "").strip().lower()
        if "replace" in txt:
            return "replace"
        # default = append
        return "append"

    def _stable_merge(self, existing: list[str], new: list[str]) -> tuple[list[str], int]:
        """
        Merge new IDs into existing list, preserving order and removing case-insensitive duplicates.

        Args:
            existing (list[str]): Existing list of article IDs.
            new (list[str]): New list of article IDs to merge.

        Returns:
            tuple[list[str], int]: Merged list of article IDs and count of duplicates skipped.
        """
        seen_lower = set(s.lower() for s in existing)
        merged = list(existing)  # keep original order
        dupes = 0
        for x in new:
            xl = x.lower()
            if xl in seen_lower:
                dupes += 1
                continue
            seen_lower.add(xl)
            merged.append(x)
        return merged, dupes

    def _normalize_ids(self, ids: list[str]) -> list[str]:
        """ Trim whitespace from IDs. """
        return [s.strip() for s in ids if s and s.strip()]

    def _capture_selection_state(self) -> dict[str, bool]:
        """
        Capture the current selection state of article IDs in the tree view.

        Args:
            None

        Returns:
            dict[str, bool]: Mapping of article ID to its selection state 
               (True if checked, False if unchecked).
        """
        state: dict[str, bool] = {}
        for i in range(self.tree.topLevelItemCount()):
            top: QTreeWidgetItem = self.tree.topLevelItem(i)
            for j in range(top.childCount()):
                child: QTreeWidgetItem = top.child(j)
                aid: str = child.data(0, Qt.UserRole)
                row: QWidget = self.tree.itemWidget(child, 0)
                if row and hasattr(row, "checkbox"):
                    state[aid] = row.checkbox.isChecked()
        return state

    def _set_pending_selection_state(self, state: dict[str, bool] | None) -> None:
        """ Set a one-time pending selection state to be applied after tree rebuild. """
        self._pending_selection_state: dict[str, bool] = state or {}


    @staticmethod
    def _normalize_list(ids_like: list[str] | None) -> list[str]:
        """ Trim whitespace; keep original casing for display """
        return [s.strip() for s in (ids_like or []) if s and s.strip()]

    @staticmethod
    def _is_valid_pmid(token: str) -> bool:
        """ Check if token is all digits (PMID) """
        return token.isdigit()

    @staticmethod
    def _is_valid_pmcid(token: str) -> bool:
        """ Check if token matches PMCID pattern """
        return PMCID_RE.match(token) is not None
