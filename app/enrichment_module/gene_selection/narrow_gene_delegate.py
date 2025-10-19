"""Provides a custom delegate for rendering narrow gene rows in the gene selection list"""

# --- Third Party Imports ---
from PyQt5.QtCore import QModelIndex, QSize, Qt
from PyQt5.QtGui import QFont, QFontMetrics, QPainter
from PyQt5.QtWidgets import QStyle, QStyledItemDelegate, QStyleOptionViewItem

# --- Local Imports ---
from app.enrichment_module.gene_selection.gene_roles import GeneRoles

# --- Public Classes ---


class NarrowGeneDelegate(QStyledItemDelegate):
    """Delegate for rendering narrow gene rows in the gene selection list."""

    def __init__(self, get_header_mode, parent=None):
        """Delegate for rendering narrow gene rows in the gene selection list."""
        super().__init__(parent)
        self._get_header_mode = get_header_mode

    def paint(self, p: QPainter, opt: QStyleOptionViewItem, idx: QModelIndex) -> None:
        """Custom paint method to render gene information in a card-like style.

        Args:
            p (QPainter): Painter object.
            opt (QStyleOptionViewItem): Style options for the item.
            idx (QModelIndex): Model index of the item.
        """

        # Draw background and border
        p.save()
        r = opt.rect.adjusted(6, 8, -6, -8)
        p.fillRect(r, opt.palette.highlight() if (
            opt.state & QStyle.State_Selected) else opt.palette.base())
        p.setPen(opt.palette.mid().color())
        p.drawRoundedRect(r, 6, 6)

        # Fetch gene data
        m = idx.model()
        sym = m.data(idx, GeneRoles.SYMBOL) or ""
        ent = m.data(idx, GeneRoles.ENTrez) or ""
        ann = m.data(idx, GeneRoles.ANN) or 0
        gfidf = m.data(idx, GeneRoles.GFIDF) or 0.0
        tax = m.data(idx, GeneRoles.TAX) or ""

        # Prepare text
        header_mode = self._get_header_mode()
        title = sym if header_mode == "Symbol" else ent if header_mode == "Entrez ID" else (
            f"{sym} • {ent}" if (sym and ent) else (sym or ent or "(gene)"))
        subtitle = f"{ann} ann  -  GF-IDF {gfidf:.3f}"
        tax_s = str(tax)
        if len(tax_s) > 22:
            tax_s = tax_s[:20] + "…"

        # Draw text
        pad = 10
        inner = r.adjusted(pad, pad, -pad, -pad)
        fm_b = QFontMetrics(self._bold(opt.font))
        fm = QFontMetrics(opt.font)
        title = fm_b.elidedText(title, Qt.ElideRight, inner.width())
        subtitle = fm.elidedText(subtitle, Qt.ElideRight, inner.width())
        chips = fm.elidedText(tax_s, Qt.ElideRight, inner.width())

        # Render text
        p.setFont(self._bold(opt.font))
        p.setPen(opt.palette.text().color())
        p.drawText(inner, Qt.AlignLeft | Qt.AlignTop, title)
        p.setFont(opt.font)
        p.setPen(opt.palette.mid().color())
        p.drawText(inner.adjusted(0, fm_b.height()+4, 0, 0),
                   Qt.AlignLeft | Qt.AlignTop, subtitle)
        p.drawText(inner.adjusted(0, fm_b.height()+fm.height() +
                   8, 0, 0), Qt.AlignLeft | Qt.AlignTop, chips)
        p.restore()

    def sizeHint(self, opt: QStyleOptionViewItem, idx: QModelIndex) -> QSize:
        """Provide size hint for each gene row.

        Args:
            opt (QStyleOptionViewItem): Style options for the item.
            idx (QModelIndex): Model index of the item.
        Returns:
            QSize: Size hint for the item.
        """
        fh = QFontMetrics(opt.font).height()
        # slightly taller to increase spacing between rows at ca 500px width
        return QSize(opt.rect.width(), 4 + 3*fh + 24)

    def _bold(self, f: QFont) -> QFont:
        """Return a bold version of the given font."""
        fb = QFont(f)
        fb.setBold(True)
        return fb
