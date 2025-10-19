"""Clickable QWidget and IconTextButton/IconTextLabel widgets"""

# --- Third Party Imports ---
from PyQt5.QtCore import QEvent, Qt, pyqtSignal
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QWidget

# --- Local Imports ---
from app.util_widgets.svg_button import SvgButton, SvgHoverButton


# --- Public Classes ---
class ClickableContainer(QWidget):
    """A QWidget that emits clicked() when pressed."""
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_Hover, True)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setCursor(Qt.PointingHandCursor)

    def event(self, e):
        """Handle hover events to update styles."""
        if e.type() == QEvent.HoverEnter:
            self.setProperty("hover", True)
            self.style().unpolish(self)
            self.style().polish(self)
        elif e.type() == QEvent.HoverLeave:
            self.setProperty("hover", False)
            self.style().unpolish(self)
            self.style().polish(self)
        return super().event(e)

    def mousePressEvent(self, e):
        """Handle mouse press events to update styles."""
        if e.button() == Qt.LeftButton:
            self.setProperty("pressed", True)
            self.style().unpolish(self)
            self.style().polish(self)
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        """Handle mouse release events to emit clicked signal and update styles."""
        if self.property("pressed"):
            self.setProperty("pressed", False)
            self.style().unpolish(self)
            self.style().polish(self)
            if e.button() == Qt.LeftButton and self.rect().contains(e.pos()):
                self.clicked.emit()
        super().mouseReleaseEvent(e)


class IconTextButton(QWidget):
    """A clickable widget with an icon and text label."""
    clicked = pyqtSignal()

    def __init__(self, text, base_name, tool_tip, icon_size, fct, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_Hover, True)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setCursor(Qt.PointingHandCursor)

        self.setObjectName("clickableWidget")

        # layout "padding"
        self.button_layout = QHBoxLayout(self)
        self.button_layout.setContentsMargins(10, 0, 0, 0)
        self.setFixedHeight(30)
        self.button_layout.setSpacing(8)

        self.btn = SvgHoverButton(
            base_name=base_name,
            tooltip=tool_tip,
            triggered_func=fct,
            size=icon_size,
            parent=parent
        )

        try:
            self.btn.setFlat(True)
        except Exception:
            pass
        self.btn.setStyleSheet("background: transparent; border: none;")

        # Style: use dynamic properties for hover/pressed
        self.setStyleSheet("""
            #clickableWidget {
                background: #0F739E;
                color: #FFFFFF;
                border: 1px solid #0F739E;
                border-radius: 4px;
                font-weight: 600;
                /* padding is handled by layout margins */
            }
            /* hover state */
            #clickableWidget[hover="true"] {
                background: #0F8088;
                border-color: #0F8088;
            }
            /* pressed state via dynamic property */
            #clickableWidget[pressed="true"] {
                background: #0E5B52;
                border-color: #0E5B52;
            }

            #clickableWidget:disabled {
                background: #E1E6EA;
                border-color: #E1E6EA;
                color: #6A7A89;
            }
            """)

        self.button_layout.addWidget(self.btn)
        self.label = QLabel(text)
        self.label.setStyleSheet(
            "background-color: transparent; color: white; font-weight: 600; border: none;")
        self.button_layout.addWidget(self.label)
        if fct is not None:
            self.clicked.connect(fct)

    def get_layout(self):
        """Get the layout of the widget."""
        return self.button_layout

    def event(self, e):
        """Handle hover events to update styles."""
        if e.type() == QEvent.HoverEnter:
            self.setProperty("hover", True)
            self.style().unpolish(self)
            self.style().polish(self)
        elif e.type() == QEvent.HoverLeave:
            self.setProperty("hover", False)
            self.style().unpolish(self)
            self.style().polish(self)
        return super().event(e)

    def mousePressEvent(self, e):
        """Handle mouse press events to update styles."""
        if e.button() == Qt.LeftButton:
            self.setProperty("pressed", True)
            self.style().unpolish(self)
            self.style().polish(self)
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        """Handle mouse release events to emit clicked signal and update styles."""
        if self.property("pressed"):
            self.setProperty("pressed", False)
            self.style().unpolish(self)
            self.style().polish(self)
            if e.button() == Qt.LeftButton and self.rect().contains(e.pos()):
                self.clicked.emit()
        super().mouseReleaseEvent(e)


class IconTextLabel(QWidget):
    """A non-clickable widget with an icon and text label."""

    def __init__(self, text, base_name, tool_tip, icon_size, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_Hover, True)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("fakeClickableWidget")

        # layout "padding"
        self.button_layout = QHBoxLayout(self)
        self.button_layout.setContentsMargins(10, 0, 0, 0)
        self.setFixedHeight(30)
        self.button_layout.setSpacing(8)

        if base_name is not None:
            self.btn = SvgButton(
                svg_file_name=base_name,
                tooltip=tool_tip,
                triggered_func=None,
                size=icon_size,
                parent=parent
            )

            try:
                self.btn.setFlat(True)
            except Exception:
                pass
            self.btn.setStyleSheet("background: transparent; border: none;")

            self.button_layout.addWidget(self.btn)

        self.setStyleSheet("""
            #fakeClickableWidget {
                background: #0F739E;
                color: #FFFFFF;
                border: 1px solid #0F739E;
                border-radius: 4px;
                font-weight: 600;
                /* padding is handled by layout margins */
            }
            """)

        self.label = QLabel(text)
        self.label.setStyleSheet(
            "background-color: transparent; color: white; font-weight: 600; border: none;")

        self.button_layout.addWidget(self.label)

    def get_layout(self):
        """Get the layout of the widget."""
        return self.button_layout
