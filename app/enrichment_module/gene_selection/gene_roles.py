"""Defines custom roles for gene data in the enrichment module"""

# --- Third Party Imports ---
from PyQt5.QtCore import Qt


# --- Public Classes ---
class GeneRoles:
    """Custom roles for gene data in the enrichment module."""
    SYMBOL = Qt.UserRole + 1
    ENTrez = Qt.UserRole + 2
    ANN = Qt.UserRole + 3
    GFIDF = Qt.UserRole + 4
    TAX = Qt.UserRole + 5
    DATA = Qt.UserRole + 6
    SEARCH = Qt.UserRole + 7
