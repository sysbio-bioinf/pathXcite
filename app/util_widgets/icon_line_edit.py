"""A QLineEdit with an embedded SVG icon button"""

# --- Third Party Imports ---
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLineEdit, QStyle

# --- Local Imports ---
from app.util_widgets.svg_button import SvgHoverButton

# --- Public Classes ---


class IconLineEdit(QLineEdit):
    """A QLineEdit with an embedded SVG icon button."""

    def __init__(self, svg_path, tooltip=None, on_click=None, on_return=None, on_text_changed=None,
                 icon_size=18, icon_position="left", parent=None):
        super().__init__(parent)

        self._btn = SvgHoverButton(base_name=svg_path, tooltip=tooltip,
                                   triggered_func=on_click, size=icon_size, parent=self)
        self._icon_position = "left" if icon_position.lower() in (
            "left", "leading") else "right"

        # Reserve space for the icon inside the text area
        pad = self._btn.width() + 4
        if self._icon_position == "left":
            self.setTextMargins(pad, 0, 0, 0)
        else:
            self.setTextMargins(0, 0, pad, 0)

        # Make sure the control is tall enough for both text and icon
        self.setMinimumHeight(
            max(self.sizeHint().height(), self._btn.height()))
        self.setAlignment(Qt.AlignVCenter)

        self._reposition_icon()  # initial placement

        if on_return is not None:
            self.returnPressed.connect(on_return)

        if on_text_changed is not None:
            self.textChanged.connect(on_text_changed)

    # --- Public Functions ---
    def resizeEvent(self, e) -> None:
        """Handle resize events to reposition the icon button."""
        super().resizeEvent(e)
        self._reposition_icon()

    # --- Private Functions ---
    def _reposition_icon(self) -> None:
        """Position the icon button inside the line edit."""
        fw = self.style().pixelMetric(QStyle.PM_DefaultFrameWidth, None, self)
        y = (self.height() - self._btn.height()) // 2

        if self._icon_position == "left":
            x = fw + 2
        else:
            x = self.width() - fw - self._btn.width() - 2

        self._btn.move(x, y)
