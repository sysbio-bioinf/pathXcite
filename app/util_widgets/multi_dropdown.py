"""A toolbar-friendly multi-select dropdown button with checkable items"""

# --- Third Party Imports ---
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QLabel


# --- Public Classes ---
class MultiSelectDropdownToolButton(QtWidgets.QWidget):
    """A toolbar-friendly multi-select dropdown button with checkable items."""
    selectionChanged = QtCore.pyqtSignal(list)

    def __init__(self, base_text="Select items...",
                 items=None, parent=None,
                 main_app=None,
                 button=None,
                 collapsed_visual=None,
                 expanded_visual=None,
                 on_selection_change=None,
                 ):
        super().__init__(parent)

        self.items = items or []
        self._base_text = base_text
        self._collapsed_text = base_text
        self._expanded_text = base_text
        self.main_app = main_app
        self._collapsed_visual = collapsed_visual
        self._expanded_visual = expanded_visual
        self._on_selection_change = on_selection_change

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
        self.label = QLabel("Show All Species' Genes")
        lay.addWidget(self.label)

        # --- menu setup ---
        self.menu = QtWidgets.QMenu(self)
        self.menu.aboutToShow.connect(self._on_menu_show)
        self.menu.aboutToHide.connect(self._on_menu_hide)

        self._content = QtWidgets.QWidget(self.menu)
        self._vbox = QtWidgets.QVBoxLayout(self._content)
        self._vbox.setContentsMargins(6, 6, 6, 6)
        self._vbox.setSpacing(6)

        self._list_widget = QtWidgets.QListWidget(self._content)
        self._list_widget.setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarAsNeeded)
        self._list_widget.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarAsNeeded)
        self._list_widget.setMaximumHeight(350)
        self._list_widget.itemChanged.connect(self._on_item_changed)
        self._vbox.addWidget(self._list_widget)

        wa = QtWidgets.QWidgetAction(self.menu)
        wa.setDefaultWidget(self._content)
        self.menu.addAction(wa)

        self._apply_visual(self._collapsed_visual)
        if items:
            self.set_options(items)
        else:
            # ensure initial UI text is correct and initial notify uses "all"
            self._update_button_text()
            # self._notify_selection_listeners()

    # --- Public Functions ---

    def eventFilter(self, obj, ev):
        """Event filter to catch button clicks."""
        if obj is self.button:
            if ev.type() == QtCore.QEvent.MouseButtonRelease and ev.button() == QtCore.Qt.LeftButton:
                self._toggle_menu()
                return True
            if ev.type() == QtCore.QEvent.MouseButtonPress and ev.button() == QtCore.Qt.LeftButton:
                return True
        return super().eventFilter(obj, ev)

    def set_options(self, items):
        """Set the list of selectable items."""
        self.items = list(items)
        self._list_widget.clear()
        for item in self.items:
            list_item = QtWidgets.QListWidgetItem(item)
            list_item.setFlags(QtCore.Qt.ItemIsUserCheckable |
                               QtCore.Qt.ItemIsEnabled)
            list_item.setCheckState(QtCore.Qt.Unchecked)
            self._list_widget.addItem(list_item)
        self._update_button_text()
        self._notify_selection_listeners()

    def get_selected_items(self, include_unchecked=False):
        """Return a list of selected (checked) items. 
        If none are checked and include_unchecked is True, return all items."""
        selected = [
            self._list_widget.item(i).text()
            for i in range(self._list_widget.count())
            if self._list_widget.item(i).checkState() == QtCore.Qt.Checked
        ]

        # If nothing is checked, return the full list
        if not selected and include_unchecked:
            selected = [
                self._list_widget.item(i).text()
                for i in range(self._list_widget.count())
            ]

        return selected

    def get_all_items(self):
        """Return a list of all items in the dropdown."""
        return [
            self._list_widget.item(i).text()
            for i in range(self._list_widget.count())
        ]

    def get_effective_selection(self):
        """Return checked items; if none are checked, return all items."""
        selected = self.get_selected_items()
        return selected if selected else list(self.items)

    def set_selected_items(self, selected_items):
        """Set the selected (checked) items in the dropdown."""
        for i in range(self._list_widget.count()):
            item = self._list_widget.item(i)
            item.setCheckState(
                QtCore.Qt.Checked if item.text() in selected_items else QtCore.Qt.Unchecked
            )
        self._update_button_text()
        self._notify_selection_listeners()

    # --- Private Functions ---
    def _wire_activation(self, btn):
        """Wire up button click to toggle the menu."""
        btn.installEventFilter(self)

    def _toggle_menu(self):
        """Show or hide the dropdown menu."""
        if self.menu.isVisible():
            self.menu.hide()
        else:
            width = max(self.button.width(), self._content.sizeHint().width())
            self._content.setMinimumWidth(width)
            self.menu.popup(self._popup_pos())

    def _popup_pos(self):
        """Calculate popup position based on toolbar orientation."""
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

    def _on_item_changed(self, item):
        """Handle an item being checked/unchecked."""
        self._update_button_text()
        # Emit raw selected (can be empty) to preserve original signal semantics
        self.selectionChanged.emit(self.get_selected_items())
        # Then notify callback/main_app with *effective* selection
        self._notify_selection_listeners()

    def _update_button_text(self):
        """Update the button text based on current selection."""
        raw_count = len(self.get_selected_items())
        if hasattr(self.button, "setText"):
            if raw_count == 0:
                self.button.setText("Select items")
                self.label.setText("Show All Species' Genes")
            elif raw_count == 1:
                self.button.setText("1 item selected")
                self.label.setText("Species Filter Set (1 Selected)")
            else:
                self.button.setText(f"{raw_count} items selected")
                self.label.setText(
                    f"Species Filter Set ({raw_count} Selected)")

    def _notify_selection_listeners(self):
        """Call the callback and/or main_app with the effective selection."""
        effective = self.get_effective_selection()

        if callable(self._on_selection_change):
            try:
                self._on_selection_change(effective)

            except Exception:
                # Avoid crashing UI if user callback throws
                QtCore.qWarning(
                    "on_selection_change callback raised an exception")
        elif self.main_app is not None and hasattr(self.main_app, "species_changed"):
            try:
                self.main_app.species_changed(effective)
            except Exception:
                QtCore.qWarning("main_app.species_changed raised an exception")
