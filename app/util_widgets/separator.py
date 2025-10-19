"""A simple separator widget (vertical or horizontal line)"""

# --- Third Party Imports ---
from PyQt5.QtWidgets import QFrame

# --- Public Functions ---


def get_separator(direction="vertical"):
    """Create and return a separator line widget."""
    separator = QFrame()
    separator.setFrameShape(QFrame.VLine if direction ==
                            "vertical" else QFrame.HLine)
    separator.setFrameShadow(QFrame.Sunken)
    return separator
