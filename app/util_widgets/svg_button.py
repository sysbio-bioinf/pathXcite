"""SVG-based icon button widgets with hover and active states"""

# --- Third Party Imports ---
from PyQt5.QtCore import QRectF, QSize, Qt
from PyQt5.QtGui import QPainter
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtWidgets import QToolButton, QWidget

# --- Local Imports ---
from app.utils import resource_path


# --- Public Classes ---
class SvgButton(QToolButton):
    """A QToolButton that displays a single SVG icon."""

    def __init__(self, svg_file_name, tooltip=None, triggered_func=None, size=24, parent=None):
        super().__init__(parent)

        # Load and store SVG renderer
        self.svg_renderer = QSvgRenderer(
            str(resource_path(f"assets/icons/{svg_file_name}")))

        # Icon size setup
        self.icon_size = QSize(size, size) if isinstance(size, int) else size
        self.setFixedSize(self.icon_size.width() + 8,
                          self.icon_size.height() + 8)

        if tooltip is not None:
            self.setToolTip(tooltip)

        # Connect the triggered function to clicked signal
        if triggered_func is not None:
            self.clicked.connect(triggered_func)
            self.setCursor(Qt.PointingHandCursor)

        # Styling and cursor

        self.setStyleSheet("""
            QToolButton {
                border: none;
                border-radius: 0px;
                padding: 4px;
                background-color: transparent;
            }
        """)

    # --- Public Functions ---
    def paintEvent(self, event):
        """Paint the SVG icon onto the button."""
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect().adjusted(4, 4, -4, -4))  # Padding
        self.svg_renderer.render(painter, rect)


class SvgHoverButton(QToolButton):
    """A QToolButton that swaps SVG icons on hover."""

    def __init__(self, base_name, tooltip=None, triggered_func=None, size=24,
                 parent=None, width=None, height=None):
        super().__init__(parent)

        self.base_name = base_name
        if width is not None and height is not None:
            self.icon_size = QSize(width, height)
        else:
            self.icon_size = QSize(size, size) if isinstance(
                size, int) else size
        self.setFixedSize(self.icon_size.width() + 8,
                          self.icon_size.height() + 8)

        # Preload SVG renderers
        self._renderer_inactive = self._load_renderer(
            f"{base_name}_inactive.svg")
        self._renderer_hover = self._load_renderer(
            f"{base_name}_hover.svg", fallback=self._renderer_inactive)
        self._current_renderer = self._renderer_inactive

        if tooltip:
            self.setToolTip(tooltip)

        if triggered_func is not None:
            self.clicked.connect(triggered_func)

        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            QToolButton {
                border: none;
                border-radius: 0px;
                padding: 4px;
                background-color: transparent;
            }
        """)
        self.setMouseTracking(True)

    # --- Public Functions ---

    def enterEvent(self, event):
        """Swap to hover renderer on mouse enter."""
        self._current_renderer = self._renderer_hover if self._renderer_hover.isValid(
        ) else self._renderer_inactive
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Swap back to inactive renderer on mouse leave."""
        self._current_renderer = self._renderer_inactive
        self.update()
        super().leaveEvent(event)

    def setBaseName(self, base_name):
        """Reload renderers for a new base name."""
        self.base_name = base_name
        self._renderer_inactive = self._load_renderer(
            f"{base_name}_inactive.svg")
        self._renderer_hover = self._load_renderer(
            f"{base_name}_hover.svg", fallback=self._renderer_inactive)
        self._current_renderer = self._renderer_inactive
        self.update()

    def paintEvent(self, event):
        """Paint the current SVG icon onto the button."""
        super().paintEvent(event)
        if not self._current_renderer or not self._current_renderer.isValid():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect().adjusted(4, 4, -4, -4))
        self._current_renderer.render(painter, rect)

    def setInactive(self):
        """Set the button to inactive state."""
        self._current_renderer = self._renderer_inactive
        self.update()

    def setHover(self):
        """Set the button to hover state."""
        self._current_renderer = self._renderer_hover if self._renderer_hover.isValid(
        ) else self._renderer_inactive
        self.update()

    # --- Private Functions ---
    def _load_renderer(self, filename, fallback=None):
        """Load an SVG renderer from file, with optional fallback."""
        path = resource_path(f"assets/icons/{filename}")
        renderer = QSvgRenderer(str(path))
        if renderer.isValid():
            return renderer
        # Fallback (e.g., if hover asset is missing)
        return fallback if fallback is not None else QSvgRenderer()


class SvgToggleButton(QToolButton):
    """
    A toggle QToolButton that represents two actions:show and collapse.
    It loads 4 icons based on the base name:
        {base}_show_inactive.svg
        {base}_show_hover.svg
        {base}_collapse_inactive.svg
        {base}_collapse_hover.svg

    The displayed icon always reflects the next action that will occur when clicked.
    """

    def __init__(
        self,
        base_name,
        tooltip=None,
        show_func=None,
        collapse_func=None,
        size=24,
        parent=None,
        width=None,
        height=None,
        initial_action="show",  # or "collapse"
    ):
        super().__init__(parent)

        self.base_name = base_name
        self.show_func = show_func
        self.collapse_func = collapse_func

        # Size handling
        if width is not None and height is not None:
            self.icon_size = QSize(width, height)
        else:
            self.icon_size = QSize(size, size) if isinstance(
                size, int) else size
        self.setFixedSize(self.icon_size.width() + 8,
                          self.icon_size.height() + 8)

        # Load renderers for both actions
        self._renderers = {
            "show": {
                "inactive": self._load_renderer(f"{base_name}_show_inactive.svg"),
                "hover":   None,  # filled below with fallback
            },
            "collapse": {
                "inactive": self._load_renderer(f"{base_name}_collapse_inactive.svg"),
                "hover":   None,
            },
        }
        # Hover fallbacks
        self._renderers["show"]["hover"] = self._load_renderer(
            f"{base_name}_show_hover.svg",
            fallback=self._renderers["show"]["inactive"]
        )
        self._renderers["collapse"]["hover"] = self._load_renderer(
            f"{base_name}_collapse_hover.svg",
            fallback=self._renderers["collapse"]["inactive"]
        )

        # The action that will be triggered on click
        self._next_action = "show" if initial_action not in (
            "show", "collapse") else initial_action
        self._is_hovered = False
        self._current_renderer = None
        self._update_icon()

        if tooltip:
            self.setToolTip(tooltip)

        self.clicked.connect(self._on_clicked)

        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            QToolButton {
                border: none;
                border-radius: 0px;
                padding: 4px;
                background-color: transparent;
            }
        """)
        self.setMouseTracking(True)

    # --- Public Functions ---

    def set_base_name(self, base_name):
        """Reload all four renderers for a new base name."""
        self.base_name = base_name
        self._renderers["show"]["inactive"] = self._load_renderer(
            f"{base_name}_show_inactive.svg")
        self._renderers["show"]["hover"] = self._load_renderer(
            f"{base_name}_show_hover.svg",
            fallback=self._renderers["show"]["inactive"]
        )
        self._renderers["collapse"]["inactive"] = self._load_renderer(
            f"{base_name}_collapse_inactive.svg")
        self._renderers["collapse"]["hover"] = self._load_renderer(
            f"{base_name}_collapse_hover.svg",
            fallback=self._renderers["collapse"]["inactive"]
        )
        self._update_icon()

    def set_actions(self, show_func=None, collapse_func=None):
        """Update the callbacks."""
        if show_func is not None:
            self.show_func = show_func
        if collapse_func is not None:
            self.collapse_func = collapse_func

    def set_next_action(self, action):
        """
        Force what the next click will do ("show" or "collapse"),
        and update the icon to match.
        """
        if action in ("show", "collapse"):
            self._next_action = action
            self._update_icon()

    def next_action(self):
        """Return the action that will happen on next click."""
        return self._next_action

    def enterEvent(self, event):
        """Handle mouse enter: set hover state and update icon."""
        self._is_hovered = True
        self._update_icon()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Handle mouse leave: unset hover state and update icon."""
        self._is_hovered = False
        self._update_icon()
        super().leaveEvent(event)

    def paintEvent(self, event):
        """Paint the current SVG icon onto the button."""
        super().paintEvent(event)
        if not self._current_renderer or not self._current_renderer.isValid():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect().adjusted(4, 4, -4, -4))  # keep padding
        self._current_renderer.render(painter, rect)

    # --- Private Functions ---

    def _load_renderer(self, filename, fallback=None):
        """Load an SVG renderer from file, with optional fallback."""
        path = resource_path(f"assets/icons/{filename}")
        renderer = QSvgRenderer(str(path))
        if renderer.isValid():
            return renderer
        return fallback if fallback is not None else QSvgRenderer()

    def _renderer_for_state(self, action, hovered):
        """Return the appropriate renderer for the given action and hover state."""
        state = "hover" if hovered else "inactive"
        r = self._renderers[action][state]
        # If somehow invalid, fall back to inactive, then empty renderer
        if not r or not r.isValid():
            r = self._renderers[action]["inactive"]
        return r if r and r.isValid() else QSvgRenderer()

    def _update_icon(self):
        """Update the current renderer based on next action and hover state."""
        self._current_renderer = self._renderer_for_state(
            self._next_action, self._is_hovered)
        self.update()

    def _on_clicked(self):
        """
        Invoke the current action's function, then swap to the other action.
        """
        if self._next_action == "show":
            if callable(self.show_func):
                self.show_func()
            self._next_action = "collapse"
        else:
            if callable(self.collapse_func):
                self.collapse_func()
            self._next_action = "show"

        self._update_icon()


class SvgClickableWidget(QWidget):
    """A clickable widget that displays an SVG icon."""

    def __init__(self, svg_path, tooltip=None, triggered_func=None, size=24, parent=None):
        super().__init__(parent)

        # Load and store SVG renderer
        self.svg_renderer = QSvgRenderer(
            str(resource_path(f"assets/icons/{svg_path}")))

        # Icon size setup
        self.icon_size = QSize(size, size) if isinstance(size, int) else size
        self.setFixedSize(self.icon_size.width() + 8,
                          self.icon_size.height() + 8)

        if tooltip is not None:
            self.setToolTip(tooltip)

        # Store callback function
        self.triggered_func = triggered_func

        if self.triggered_func:
            self.setCursor(Qt.PointingHandCursor)

        self.setStyleSheet("""
            QWidget {
                border: none;
                border-radius: 0px;
                padding: 4px;
                background-color: transparent;
            }
        """)

    # --- Public Functions ---
    def paintEvent(self, event):
        """Paint the current SVG icon onto the button."""
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect().adjusted(4, 4, -4, -4))  # Padding
        self.svg_renderer.render(painter, rect)

    def mousePressEvent(self, event):
        """Invoke the callback function on left mouse button press."""
        if self.triggered_func and event.button() == Qt.LeftButton:
            self.triggered_func()


class DatabaseStatusButton(QToolButton):
    """A QToolButton that indicates database availability with different SVG icons."""

    def __init__(self, available, tooltip=None, triggered_func=None, size=24, parent=None):
        super().__init__(parent)

        # Load and store SVG renderer
        if available:
            svg_path = "db_true.svg"
        else:
            svg_path = "db_false.svg"
        self.svg_renderer = QSvgRenderer(
            str(resource_path(f"assets/icons/{svg_path}")))

        # Icon size setup
        self.icon_size = QSize(size, size) if isinstance(size, int) else size
        self.setFixedSize(self.icon_size.width() + 8,
                          self.icon_size.height() + 8)

        if tooltip is not None:
            self.setToolTip(tooltip)

        # Connect the triggered function to clicked signal
        if triggered_func is not None:
            self.clicked.connect(triggered_func)

        # Styling and cursor
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
    def paintEvent(self, event):
        """Paint the SVG icon onto the button."""
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect().adjusted(4, 4, -4, -4))  # Padding
        self.svg_renderer.render(painter, rect)

    def update_icon(self, available):
        """Update the icon based on availability."""
        if available:
            self.svg_renderer.load(
                str(resource_path("assets/icons/db_true.svg")))
        else:
            self.svg_renderer.load(
                str(resource_path("assets/icons/db_false.svg")))
        self.update()
