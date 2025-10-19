"""Provides a Qt model for displaying and managing a list of genes in the enrichment module"""

# --- Third Party Imports ---
from PyQt5.QtCore import QAbstractListModel, QModelIndex, Qt, QVariant

# --- Local Imports ---
from app.enrichment_module.gene_selection.gene_roles import GeneRoles


# --- Public Classes ---
class GeneListModel(QAbstractListModel):
    """Qt model for a list of genes."""

    def __init__(self, genes=None, parent=None):
        """Qt model for a list of genes.
        Args:
            genes (list[dict], optional): List of gene dictionaries. Defaults to None.
            parent (QObject, optional): Parent QObject. Defaults to None.
        """
        super().__init__(parent)
        self._genes: list[dict] = genes or []
        self._precompute()

    # --- Public Methods ---
    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return the number of rows in the model."""
        return 0 if parent.isValid() else len(self._genes)

    def data(self, index: QModelIndex, role: int) -> QVariant:
        """Return data for a given index and role."""

        if not index.isValid():
            return QVariant()
        g = self._genes[index.row()]
        if role in (Qt.DisplayRole, Qt.EditRole):
            return f"{g.get('gene_symbol', '')} • {g.get('entrez_id', '')}"
        if role == GeneRoles.SYMBOL:
            return g.get("gene_symbol", "")
        if role == GeneRoles.ENTrez:
            return g.get("entrez_id", "")
        if role == GeneRoles.ANN:
            return int(g.get("annotations", 0) or 0)
        if role == GeneRoles.GFIDF:
            return float(g.get("gfidf", 0.0) or 0.0)
        if role == GeneRoles.TAX:
            return str(g.get("tax_id", "") or "")
        if role == GeneRoles.DATA:
            return g
        if role == GeneRoles.SEARCH:
            return g.get("_search_str", "")
        return QVariant()

    def update(self, genes: list[dict] | None) -> None:
        """Update the model with a new list of genes.
        Args:
            genes (list[dict] | None): New list of gene dictionaries.
        """
        self.beginResetModel()
        self._genes = genes or []
        self._precompute()
        self.endResetModel()

    # --- Private Methods ---

    def _precompute(self) -> None:
        """Precompute search strings for each gene for efficient searching."""
        for g in self._genes:
            g["_search_str"] = " ".join(str(x) for x in [
                g.get("gene_symbol", ""), g.get(
                    "entrez_id", ""), g.get("tax_id", ""),
                g.get("gfidf", ""), g.get("annotations", "")
            ]).lower()
