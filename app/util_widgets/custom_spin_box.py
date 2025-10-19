"""A custom spin box widget with up and down buttons and a percentage display"""

# --- Third Party Imports ---
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QWidget

# --- Local Imports ---
from app.util_widgets.svg_button import SvgButton


# --- Public Classes ---
class CustomSpinBox(QWidget):
    """A custom spin box widget with up and down buttons and a percentage display."""

    def __init__(self, number_change_fct=None, parent=None):
        super().__init__(parent)

        self.number_change_fct = number_change_fct
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel("80%", self)

        # set font of label white and background transparent
        self.label.setStyleSheet("color: white; background: transparent;")

        self.up_btn = SvgButton(
            svg_file_name="zoom_in2.svg", tooltip="Scan Page for Article IDs",
            triggered_func=lambda: self._number_up(), size=20, parent=self
        )

        self.down_btn = SvgButton(
            svg_file_name="zoom_out2.svg", tooltip="Scan Page for Article IDs",
            triggered_func=lambda: self._number_down(), size=20, parent=self
        )

        self.setLayout(self.layout)

        self.layout.addWidget(self.down_btn)
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.up_btn)

    # --- Private Functions ---
    def _number_up(self) -> None:
        """Increase the percentage value."""
        current_value = int(self.label.text().strip('%'))
        if current_value < 300:
            new_value = current_value + 10
            self.label.setText(f"{new_value}%")

            if self.number_change_fct:
                self.number_change_fct(new_value)

    def _number_down(self) -> None:
        """Decrease the percentage value."""
        current_value = int(self.label.text().strip('%'))
        if current_value > 10:
            new_value = current_value - 10
            self.label.setText(f"{new_value}%")

            if self.number_change_fct:
                self.number_change_fct(new_value)
