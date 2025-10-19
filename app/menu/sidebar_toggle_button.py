"""Sidebar toggle button widget"""

# --- Third Party Imports ---
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QHBoxLayout, QWidget

# --- Local Imports ---
from app.util_widgets.svg_button import SvgButton
from app.utils import resource_path


# -- Public Classes ---
class SidebarToggleButton(QWidget):
    """ A button to toggle the sidebar between collapsed and expanded states. """

    def __init__(self, collapsed: bool = False, size: int = 24, callback=None, parent=None):
        """Initializes a sidebar toggle button to expand/collapse the sidebar.
        Args:
            collapsed: True if the sidebar is collapsed, False otherwise.
            size: Size of the button.
            callback: Function to call when the button is clicked.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.callback = callback
        self.collapsed = collapsed
        # self.is_hovered = False
        self.is_active = False

        svg_path = self._svg_path("inactive")
        self.icon_widget = SvgButton(
            # Extract just the filename
            svg_file_name=svg_path.rsplit('/', maxsplit=1)[-1],
            tooltip="Scan Page for Article IDs",
            triggered_func=lambda: self.callback(),
            size=24
        )
        self._update_icon("inactive")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.addWidget(self.icon_widget)

        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Expand Menu" if self.collapsed else "Collapse Menu")

    # --- Public Methods ---

    def set_collapsed(self, collapsed: bool) -> None:
        """Sets the collapsed state of the button.
        Args:
            collapsed: True if the sidebar is collapsed, False otherwise.
        """
        self.collapsed = collapsed
        self.setToolTip("Expand Menu" if self.collapsed else "Collapse Menu")
        self._update_icon("inactive")

    def enterEvent(self, event):
        """Handles mouse enter event to update icon."""
        self._update_icon("hover")

    def leaveEvent(self, event):
        """Handles mouse leave event to update icon."""
        self._update_icon("inactive")

    # --- Private Methods ---

    def _svg_path(self, state: str) -> str:
        """Generates the SVG file name based on the collapsed state and button state.
        Args:
            state: The state of the button ('active', 'inactive', 'hover').
        Returns:
            The SVG file name.
        """
        base = "expand" if self.collapsed else "collapse"
        return str(resource_path(f"assets/icons/{base}_{state}.svg"))

    def _update_icon(self, state: str) -> None:
        """Updates the icon based on the button state."""
        path = self._svg_path(state)
        self.icon_widget.svg_renderer.load(path)
        self.icon_widget.update()
