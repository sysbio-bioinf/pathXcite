"""A collapsible section widget with a header and content area"""

# --- Third Party Imports ---
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QHBoxLayout, QToolButton, QVBoxLayout, QWidget


# --- Public Classes ---
class CollapsibleSection(QWidget):
    """A collapsible section widget with a header and content area."""

    def __init__(self, title: str, start_collapsed: bool = False, parent=None):
        super().__init__(parent)

        # Header bar
        self.toggle_btn = QToolButton(text=title, checkable=True)
        self.toggle_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toggle_btn.setChecked(not start_collapsed)
        self.toggle_btn.setArrowType(
            Qt.DownArrow if not start_collapsed else Qt.RightArrow)

        self.header_right = QWidget()
        self.header_right.setLayout(QHBoxLayout())
        self.header_right.layout().setContentsMargins(0, 0, 0, 0)
        self.header_right.layout().setSpacing(6)

        header_bar = QWidget()
        header_bar.setLayout(QHBoxLayout())
        header_bar.layout().setContentsMargins(0, 0, 0, 0)
        header_bar.layout().addWidget(self.toggle_btn)
        header_bar.layout().addStretch()
        header_bar.layout().addWidget(self.header_right)

        # Content area
        self.content = QWidget()
        self.content.setLayout(QVBoxLayout())
        self.content.layout().setContentsMargins(0, 0, 0, 0)
        self.content.setVisible(not start_collapsed)

        # Wire up toggle
        self.toggle_btn.toggled.connect(self._on_toggled)

        # Main layout
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(6)
        outer.addWidget(header_bar)
        outer.addWidget(self.content)

    def _on_toggled(self, expanded: bool) -> None:
        """Handle toggle button state change."""
        self.content.setVisible(expanded)
        self.toggle_btn.setArrowType(
            Qt.DownArrow if expanded else Qt.RightArrow)

    @property
    def content_layout(self) -> QVBoxLayout:
        """Get the layout of the content area."""
        return self.content.layout()

    @property
    def header_right_layout(self) -> QHBoxLayout:
        """Get the layout of the header right area."""
        return self.header_right.layout()
