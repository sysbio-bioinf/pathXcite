"""A toolbar-friendly single-select dropdown button with checkable items"""

# --- Third Party Imports ---
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QLabel, QScrollArea

# --- Public Classes ---


class SingleSelectDropdownToolButton(QtWidgets.QWidget):
    """A toolbar-friendly single-select dropdown button with checkable items."""
    selectionChanged = QtCore.pyqtSignal(list)

    def __init__(self, base_text="Select items...",
                 items=None, parent=None,
                 button=None,
                 collapsed_visual=None,
                 expanded_visual=None,
                 item_name="Library"):
        super().__init__(parent)

        self._base_text = base_text
        self._collapsed_text = base_text
        self._expanded_text = base_text
        self.item_name = item_name
        self._collapsed_visual = collapsed_visual
        self._expanded_visual = expanded_visual

        # --- visible button ---
        if button is None:
            btn = QtWidgets.QToolButton(self)
            btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
            btn.setAutoRaise(True)
            btn.setText(self._collapsed_text)
        else:
            btn = button
            btn.setParent(self)

        self.button = btn
        self._wire_activation(self.button)

        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.button)

        self.label = QLabel(f"No {self.item_name} Selected")
        lay.addWidget(self.label)

        # --- menu setup ---
        self.menu = QtWidgets.QMenu(self)
        self.menu.aboutToShow.connect(self._on_menu_show)
        self.menu.aboutToHide.connect(self._on_menu_hide)

        self._content = QtWidgets.QWidget(self.menu)
        self._vbox = QtWidgets.QVBoxLayout(self._content)
        self._vbox.setContentsMargins(6, 6, 6, 6)
        self._vbox.setSpacing(6)

        self.scroll_area = QScrollArea()
        self.scroll_area.setFixedHeight(200)
        self._list_widget = QtWidgets.QListWidget(self._content)
        self._list_widget.setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarAlwaysOff)
        self._list_widget.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarAlwaysOff)

        self.scroll_area.setWidget(self._list_widget)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarAsNeeded)
        self._vbox.addWidget(self.scroll_area)

        self._list_widget.itemChanged.connect(self._on_item_changed)

        wa = QtWidgets.QWidgetAction(self.menu)
        wa.setDefaultWidget(self._content)
        self.menu.addAction(wa)

        self._apply_visual(self._collapsed_visual)
        if items:
            self.set_options(items)

        # select first
        if self._list_widget.count() > 0:
            self._list_widget.item(0).setCheckState(QtCore.Qt.Checked)

    # --- Public Functions ---

    def eventFilter(self, obj, ev):
        """Handle button events to toggle the menu."""
        if obj is self.button:
            if ev.type() == QtCore.QEvent.MouseButtonRelease and ev.button() == QtCore.Qt.LeftButton:
                self._toggle_menu()
                return True

            if ev.type() == QtCore.QEvent.MouseButtonPress and ev.button() == QtCore.Qt.LeftButton:
                return True
        return super().eventFilter(obj, ev)

    def set_options(self, items):
        """Set the available options in the dropdown."""
        selected_item = self.get_selected_item()
        if selected_item not in items:
            selected_item = items[0] if items else None

        self._list_widget.clear()
        for item in items:
            list_item = QtWidgets.QListWidgetItem(item)
            list_item.setFlags(QtCore.Qt.ItemIsUserCheckable |
                               QtCore.Qt.ItemIsEnabled)
            list_item.setCheckState(QtCore.Qt.Unchecked)
            self._list_widget.addItem(list_item)
        self._update_button_text()

        if selected_item is not None:
            self.set_selected_item(selected_item)

    def get_selected_items(self):
        """Get the list of currently selected items."""
        return [
            self._list_widget.item(i).text()
            for i in range(self._list_widget.count())
            if self._list_widget.item(i).checkState() == QtCore.Qt.Checked
        ]

    def get_selected_item(self):
        """Get the currently selected item (or None if none)."""
        items = self.get_selected_items()
        return items[0] if items else None

    def set_selected_item(self, item_name):
        """Set the currently selected item by name."""
        for i in range(self._list_widget.count()):
            item = self._list_widget.item(i)
            if item.text() == item_name:
                item.setCheckState(QtCore.Qt.Checked)
            else:
                item.setCheckState(QtCore.Qt.Unchecked)
        self._update_button_text()

    # --- Private Functions ---
    def _wire_activation(self, btn):
        """
        Wire up the button to toggle the dropdown menu on click.
        """
        # Use event filter for full control
        btn.installEventFilter(self)

    def _toggle_menu(self):
        """Toggle the visibility of the dropdown menu."""
        if self.menu.isVisible():
            self.menu.hide()
        else:
            # width = max(self.button.width(), self._content.sizeHint().width())
            # self._content.setMinimumWidth(width)
            self.menu.popup(self._popup_pos())

    def _popup_pos(self):
        """Calculate the position to popup the menu."""
        tb = self._find_toolbar()
        if tb and tb.orientation() == QtCore.Qt.Vertical:
            return self.button.mapToGlobal(QtCore.QPoint(self.button.width(), 0))
        return self.button.mapToGlobal(QtCore.QPoint(0, self.button.height()))

    def _find_toolbar(self):
        """Find the parent toolbar, if any."""
        p = self.parent()
        while p is not None:
            if isinstance(p, QtWidgets.QToolBar):
                return p
            p = p.parent()
        return None

    def _on_menu_show(self):
        """Handle the dropdown menu being shown."""
        self._apply_visual(self._expanded_visual)
        if hasattr(self.button, "setHover"):
            self.button.setHover()
        if hasattr(self.button, "setText"):
            self.button.setText(self._expanded_text)

    def _on_menu_hide(self):
        """Handle the dropdown menu being hidden."""
        self._apply_visual(self._collapsed_visual)
        if hasattr(self.button, "setInactive"):
            self.button.setInactive()
        self._update_button_text()

    def _apply_visual(self, visual):
        """Apply the given visual to the button."""
        if not visual:
            return
        if callable(visual):
            visual(self.button)
            if hasattr(self.button, "update"):
                self.button.update()
            return
        if isinstance(visual, QtGui.QIcon) and hasattr(self.button, "setIcon"):
            self.button.setIcon(visual)
            if hasattr(self.button, "update"):
                self.button.update()
            return
        if isinstance(visual, str):
            for name in ("setBaseName", "setSvgName", "setSvg", "setIconName"):
                meth = getattr(self.button, name, None)
                if callable(meth):
                    meth(visual)
                    if hasattr(self.button, "update"):
                        self.button.update()
                    return
            if hasattr(self.button, "setIcon"):
                icon = QtGui.QIcon.fromTheme(visual)
                if not icon.isNull():
                    self.button.setIcon(icon)
                    if hasattr(self.button, "update"):
                        self.button.update()

    def _on_item_changed(self, changed_item):
        """Handle an item being checked/unchecked."""
        if changed_item.checkState() == QtCore.Qt.Checked:
            # Uncheck all other items
            for i in range(self._list_widget.count()):
                item = self._list_widget.item(i)
                if item is not changed_item and item.checkState() == QtCore.Qt.Checked:
                    item.setCheckState(QtCore.Qt.Unchecked)

        self._update_button_text()
        self.selectionChanged.emit(self.get_selected_items())

    def _update_button_text(self):
        """Update the button text based on current selection."""
        count = len(self.get_selected_items())
        if hasattr(self.button, "setText"):
            if count == 0:
                self.button.setText(f"Select {self.item_name}")
                self.label.setText(f"No {self.item_name} Selected")
            elif count == 1:
                self.button.setText(f"1 {self.item_name} selected")
                self.label.setText(
                    f"{self.item_name}: {self.get_selected_item()}")
            else:
                self.button.setText(f"{count} {self.item_name}s selected")
