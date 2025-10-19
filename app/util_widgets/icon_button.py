"""SVG-based icon button widgets with hover and active states"""

# --- Third Party Imports ---
from PyQt5.QtCore import QRectF, QSize, Qt
from PyQt5.QtGui import QPainter
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtWidgets import QPushButton, QToolButton

# --- Local Imports ---
from app.utils import resource_path


# --- Public Classes ---
class SvgIconButton(QPushButton):
    """A QPushButton that displays an SVG icon with hover and active states."""

    def __init__(self, svg_inactive, svg_hover, svg_active, icon_size=QSize(24, 24),
                 parent=None, main_app=None, object_name=None, callback=None):
        super().__init__(parent)
        self.main_app = main_app
        self.setObjectName(object_name)

        # Load SVG files
        svg_inactive = str(resource_path(f"assets/icons/{svg_inactive}"))
        svg_hover = str(resource_path(f"assets/icons/{svg_hover}"))
        svg_active = str(resource_path(f"assets/icons/{svg_active}"))
        self.svg_renderers = {
            'inactive': QSvgRenderer(svg_inactive),
            'hover': QSvgRenderer(svg_hover),
            'active': QSvgRenderer(svg_active)
        }

        self.icon_size = icon_size
        self.setFixedSize(icon_size.width() + 10, icon_size.height() + 10)
        self._hovered = False
        self._pressed = False
        self._is_active = False
        self.setCursor(Qt.PointingHandCursor)
        self.setFlat(True)

        if callback:
            self.clicked.connect(callback)

    # --- Public Functions ---
    def enterEvent(self, event):
        """Handle mouse hover enter event."""
        self._hovered = True
        self.update()

    def leaveEvent(self, event):
        """Handle mouse hover leave event."""
        self._hovered = False
        self.update()

    def mousePressEvent(self, event):
        """Handle mouse press event."""
        self._pressed = True
        self._is_active = True
        self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """Handle mouse release event."""
        self._pressed = False
        self.update()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        """Paint the appropriate SVG icon based on the button state."""
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if self._hovered:
            renderer = self.svg_renderers['hover']
        elif self._is_active:
            renderer = self.svg_renderers['active']
        else:
            renderer = self.svg_renderers['inactive']

        rect = QRectF(self.rect().adjusted(4, 4, -4, -4))
        renderer.render(painter, rect)

    def make_inactive(self):
        """Set the button to inactive state."""
        self._is_active = False
        self.update()

    def make_active(self):
        """Set the button to active state."""
        self._is_active = True
        self.update()


class SvgToolSimpleButton(QToolButton):
    """A simple QToolButton that displays an SVG icon."""

    def __init__(self, svg_path, tooltip=None, triggered_func=None, size=24, parent=None):
        super().__init__(parent)

        self.svg_renderer = QSvgRenderer(
            str(resource_path(f"assets/icons/{svg_path}")))
        if isinstance(size, int):
            self.icon_size = QSize(size, size)
        else:
            self.icon_size = size
        self.setFixedSize(self.icon_size.width() + 8,
                          self.icon_size.height() + 8)
        if tooltip is not None:
            self.setToolTip(tooltip)
        if triggered_func is not None:
            self.triggered_func = triggered_func

        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            QToolButton {
                border: none;
                border-radius: 0px;
                padding: 4px;
                background-color: transparent;
            }
        """)

    # --- Public Functions ---
    def paintEvent(self, event) -> None:
        """Paint the SVG icon onto the button."""
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect().adjusted(4, 4, -4, -4))
        self.svg_renderer.render(painter, rect)
