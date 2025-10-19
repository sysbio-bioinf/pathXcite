"""Sidebar menu button widget"""

# --- Third Party Imports ---
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QWidget

# --- Local Imports ---
from app.util_widgets.svg_button import SvgClickableWidget
from app.utils import resource_path


# -- Public Classes ---
class SidebarMenuButton(QWidget):
    """ A button for the sidebar menu with an icon and label. """

    def __init__(self, icon_base: str, text: str, index: int, callback=None, size: int = 24, parent=None):
        """Initializes a sidebar menu button with icon and label.
        Args:
            icon_base: Base name for the icon SVG files (without state suffix).
            text: Label text for the button.
            index: Index of the button (for callback identification).
            callback: Function to call when the button is clicked.
            size: Size of the icon.
            parent: Parent QWidget.
        """
        super().__init__(parent)
        self.index = index
        self.callback = callback
        self.icon_base = icon_base
        self.size = size

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(8, 4, 8, 4)
        self.layout.setSpacing(10)

        self.icon_widget = SvgClickableWidget(
            svg_path=self._svg_path("inactive"),
            size=size
        )
        self.layout.addWidget(self.icon_widget)

        self.icon_widget.setAttribute(Qt.WA_TransparentForMouseEvents)

        self.label = QLabel(text)
        self.label.setStyleSheet("font-size: 13px;")
        self.layout.addWidget(self.label)

        self.setCursor(Qt.PointingHandCursor)
        self.set_active(False)

        self.setStyleSheet("""
            SidebarMenuButton {
                background-color: transparent;
            }
            SidebarMenuButton:hover {
                background-color: #e0f7fa;
            }
        """)

    # --- Public Methods ---
    def set_active(self, is_active: bool) -> None:
        """Sets the button's active state.
        Args:
            is_active: True if the button is active, False otherwise.
        """
        self.is_active = is_active
        icon_state = "active" if is_active else "inactive"
        self.icon_widget.svg_renderer.load(
            str(resource_path(f"assets/icons/{self._svg_path(icon_state)}")))
        self.icon_widget.update()
        font_weight = "bold" if is_active else "normal"
        self.label.setStyleSheet(
            f"font-size: 13px; font-weight: {font_weight};")

    def set_collapsed(self, collapsed: bool) -> None:
        """Sets the collapsed state of the button.
        Args:
            collapsed: True to collapse the button, False to expand it.
        """
        self.label.setVisible(not collapsed)

    def enterEvent(self, event):
        """Handles mouse enter event to change icon on hover."""
        if not getattr(self, 'is_active', False):
            self.icon_widget.svg_renderer.load(
                str(resource_path(f"assets/icons/{self._svg_path('hover')}")))
            self.icon_widget.update()

    def leaveEvent(self, event):
        """Handles mouse leave event to revert icon."""
        if not getattr(self, 'is_active', False):
            self.icon_widget.svg_renderer.load(
                str(resource_path(f"assets/icons/{self._svg_path('inactive')}")))
            self.icon_widget.update()

    def mousePressEvent(self, event):
        """Handles mouse press event to trigger callback."""
        if event.button() == Qt.LeftButton and self.callback:
            self.callback(self.index)

    # --- Private Methods ---
    def _svg_path(self, state: str) -> str:
        """Generates the SVG file name based on the button state.
        Args:
            state: State of the button ('active', 'inactive', 'hover').
        Returns:
            The SVG file name.
        """
        return f"{self.icon_base}_{state}.svg"  # e.g., browser_active.svg
