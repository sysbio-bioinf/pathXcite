"""A toolbar-friendly dropdown button with customizable options and visuals"""

# --- Standard Library Imports ---
import inspect

# --- Third Party Imports ---
from PyQt5 import QtCore, QtGui, QtWidgets

# --- Public Classes ---


class DropdownToolButton(QtWidgets.QWidget):
    """A toolbar-friendly dropdown button with customizable options and visuals. """
    optionTriggered = QtCore.pyqtSignal(str)

    def __init__(self, base_text="",
                 options=None, parent=None, *,
                 button=None,
                 collapsed_visual=None,
                 expanded_visual=None):
        super().__init__(parent)

        self._base_text = base_text
        self._collapsed_text = base_text or ""
        self._expanded_text = base_text or ""

        self._collapsed_visual = collapsed_visual
        self._expanded_visual = expanded_visual

        # --- visible toolbar button ---
        if button is None:
            btn = QtWidgets.QToolButton(self)
            btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
            btn.setAutoRaise(True)
            if hasattr(btn, "setText"):
                btn.setText(self._collapsed_text)
        else:
            btn = button
            btn.setParent(self)

        self.button = btn
        self._wire_activation(self.button)

        # --- wrapper layout ---
        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.button)

        # --- the popover menu ---
        self.menu = QtWidgets.QMenu(self)
        self.menu.aboutToShow.connect(self._on_menu_show)
        self.menu.aboutToHide.connect(self._on_menu_hide)

        # custom content inside the menu
        self._content = QtWidgets.QWidget(self.menu)
        self._vbox = QtWidgets.QVBoxLayout(self._content)
        self._vbox.setContentsMargins(6, 6, 6, 6)
        self._vbox.setSpacing(6)

        wa = QtWidgets.QWidgetAction(self.menu)
        wa.setDefaultWidget(self._content)
        self.menu.addAction(wa)

        self._option_buttons = []
        self._apply_visual(self._collapsed_visual)  # start in collapsed state
        self.set_options(options or {})

    # --- Public Functions ---

    def eventFilter(self, obj, ev) -> bool:
        """Fallback event filter to catch mouse releases."""
        if obj is self.button and ev.type() == QtCore.QEvent.MouseButtonRelease:
            if ev.button() == QtCore.Qt.LeftButton:
                self._toggle_menu()
                return True
        return super().eventFilter(obj, ev)

    # ---------------- public api ----------------
    def set_options(self, options_dict) -> None:
        """Replace all menu options. options_dict: {text: callable}."""
        self._clear_content()

        for text, func in options_dict.items():
            btn = QtWidgets.QPushButton(text, self._content)
            btn.clicked.connect(self._make_handler(text, func))
            self._vbox.addWidget(btn)
            self._option_buttons.append(btn)

        # keep content tight
        self._vbox.addStretch(1)

    def set_visuals(self, collapsed=None, expanded=None) -> None:
        """Set the visuals for collapsed and expanded states.
        Each can be a QIcon, str (svg name), or callable(button)->None."""
        if collapsed is not None:
            self._collapsed_visual = collapsed
        if expanded is not None:
            self._expanded_visual = expanded
        self._apply_visual(self._collapsed_visual)

    # --- Private Functions ---
    def _wire_activation(self, btn) -> None:
        """Connect any reasonable activation signal; otherwise use an event filter."""
        for name in ("clicked", "triggered", "pressed", "released", "toggled"):
            sig = getattr(btn, name, None)
            if hasattr(sig, "connect"):
                sig.connect(self._toggle_menu)
                return
        btn.installEventFilter(self)

    def _clear_content(self) -> None:
        """Remove existing option buttons and trailing stretch."""
        for b in self._option_buttons:
            b.setParent(None)
            b.deleteLater()
        self._option_buttons.clear()

        # remove any extra stretches/widgets in layout
        while self._vbox.count():
            item = self._vbox.takeAt(self._vbox.count() - 1)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()

    def _make_handler(self, text, func):
        """Create a handler that emits the optionTriggered signal and calls func."""
        def handler():
            self.menu.hide()
            self.optionTriggered.emit(text)
            if callable(func):
                try:
                    func()  # prefer zero-arg
                except TypeError:
                    try:
                        sig = inspect.signature(func)
                        params = [p for p in sig.parameters.values()
                                  if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
                                  and p.default is p.empty]
                        if len(params) == 1:
                            func(text)
                        else:
                            raise
                    except Exception:
                        raise
        return handler

    def _apply_visual(self, visual) -> None:
        """Accepts QIcon, str (svg name), or callable(button)->None."""
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

    def _toggle_menu(self) -> None:
        """Show or hide the dropdown menu."""
        if self.menu.isVisible():
            self.menu.hide()
        else:
            w = max(self.button.width(), self._content.sizeHint().width())
            self._content.setMinimumWidth(w)
            self.menu.popup(self._popup_pos())

    def _on_menu_show(self) -> None:
        """Handle menu show event."""
        self._apply_visual(self._expanded_visual)
        if hasattr(self.button, "setHover"):
            self.button.setHover()
        if hasattr(self.button, "setText"):
            self.button.setText(self._expanded_text)

    def _on_menu_hide(self) -> None:
        """Handle menu hide event."""
        # Collapsed visual
        self._apply_visual(self._collapsed_visual)
        if hasattr(self.button, "setInactive"):
            self.button.setInactive()
        if hasattr(self.button, "setText"):
            self.button.setText(self._collapsed_text)

    def _popup_pos(self):
        """Calculate popup position based on toolbar orientation."""
        tb = self._find_toolbar()
        if tb and tb.orientation() == QtCore.Qt.Vertical:
            return self.button.mapToGlobal(QtCore.QPoint(self.button.width(), 0))
        return self.button.mapToGlobal(QtCore.QPoint(0, self.button.height()))

    def _find_toolbar(self):
        """Traverse parent hierarchy to find enclosing QToolBar, if any."""
        p = self.parent()
        while p is not None:
            if isinstance(p, QtWidgets.QToolBar):
                return p
            p = p.parent()
        return None
