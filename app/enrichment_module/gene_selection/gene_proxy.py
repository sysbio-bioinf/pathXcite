"""Provides a proxy model for filtering and sorting genes in the enrichment module"""

# --- Third Party Imports ---
from PyQt5.QtCore import QModelIndex, QSortFilterProxyModel, Qt

# --- Local Imports ---
from app.enrichment_module.gene_selection.gene_roles import GeneRoles


# --- Public Classes ---
class GeneProxy(QSortFilterProxyModel):
    """Proxy model for filtering and sorting genes."""

    def __init__(self, parent=None):
        """Proxy model for filtering and sorting genes."""
        super().__init__(parent)
        # self._header_mode = "Symbol + Entrez"
        self._deep_search = False
        self._sort_mode = "Annotations (desc)"
        self.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.setDynamicSortFilter(True)

    def set_header_mode(self, mode):
        """Set the header mode for display (not used in sorting)."""
        self.invalidate()

    def set_deep_search(self, enabled: bool) -> None:
        """Enable or disable deep search in annotations."""
        self._deep_search = enabled
        self.invalidateFilter()

    def set_sort_mode(self, text: str) -> None:
        """Set the sorting mode for the proxy model."""
        self._sort_mode = text
        self.sort(0, Qt.DescendingOrder if text.endswith(
            "(desc)") else Qt.AscendingOrder)

    def lessThan(self, l: QModelIndex, r: QModelIndex) -> bool:
        """Custom lessThan implementation for sorting based on the selected sort mode.

        Args:
            l (QModelIndex): Left index.
            r (QModelIndex): Right index.
        Returns:
            bool: True if the left index is less than the right index, False otherwise.
        """
        m = self.sourceModel()
        if self._sort_mode.startswith("Annotations"):
            return m.data(l, GeneRoles.ANN) < m.data(r, GeneRoles.ANN)
        if self._sort_mode.startswith("GF-IDF"):
            return m.data(l, GeneRoles.GFIDF) < m.data(r, GeneRoles.GFIDF)
        if self._sort_mode.startswith("Symbol"):
            return (m.data(l, GeneRoles.SYMBOL) or "").lower() < (m.data(r, GeneRoles.SYMBOL) or "").lower()
        return (m.data(l, GeneRoles.ENTrez) or "").lower() < (m.data(r, GeneRoles.ENTrez) or "").lower()

    def filterAcceptsRow(self, row: int, parent: QModelIndex) -> bool:
        """Custom filter to include deep search in annotations if enabled.

        Args:
            row (int): Row index.
            parent (QModelIndex): Parent index.
        Returns:
            bool: True if the row is accepted by the filter, False otherwise.
        """
        if self.filterRegExp().isEmpty():
            return True
        m = self.sourceModel()
        idx = m.index(row, 0, parent)
        q = self.filterRegExp().pattern().lower()

        if q in (m.data(idx, GeneRoles.SEARCH) or ""):
            return True

        if not self._deep_search:
            return False

        g = m.data(idx, GeneRoles.DATA) or {}
        for a in (g.get("annotation_list") or []):
            if q in str(a.get("text", "")).lower() or q in str(a.get("pubmed_id", "")).lower() or q in str(a.get("accession", "")).lower():
                return True
        return False
