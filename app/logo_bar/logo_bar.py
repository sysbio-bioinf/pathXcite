"""Top logo bar widget"""

# --- Third Party Imports ---
from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QHBoxLayout, QWidget

# --- Local Imports ---
from app.util_widgets.icon_button import SvgToolSimpleButton


# --- Public Classes ---
class LogoBar(QWidget):
    """ A widget that displays the logo bar at the top of the application. """

    def __init__(self, main_app):
        """Initializes the logo bar."""
        super().__init__()
        self.main_app = main_app
        self.db_name_to_path = {}
        # Create main layout
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Create a panel widget to hold the labels and set its background
        panel = QWidget()
        panel.setStyleSheet("background-color: #005F6B;")

        # Create a layout for the panel
        panel_layout = QHBoxLayout()
        panel_layout.setContentsMargins(5, 0, 5, 0)

        # Title logo
        title_logo_button = SvgToolSimpleButton(
            svg_path="pathxcite_logo_v3.svg",
            size=QSize(int(320 / 3.4), int(106 / 3.4))
        )

        panel_layout.addWidget(title_logo_button)
        panel_layout.addStretch(50)

        panel.setLayout(panel_layout)
        main_layout.addWidget(panel)

        self.setLayout(main_layout)
        self.setFixedHeight(40)
