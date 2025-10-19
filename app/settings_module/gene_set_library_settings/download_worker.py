"""Worker that downloads gene set libraries without blocking the UI"""

# --- Standard Library Imports ---
import os
from urllib.parse import quote

# --- Third Party Imports ---
import requests
from PyQt5.QtCore import QObject, QRegularExpression, pyqtSignal

# --- Constants ---
EMAIL_RE = QRegularExpression(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

# --- Public Classes ---


class DownloadWorker(QObject):
    """Worker that downloads gene set libraries without blocking the UI."""
    started_library = pyqtSignal(int, str)  # row, lib_name
    finished_library = pyqtSignal(int, str, bool)  # row, lib_name, success
    all_done = pyqtSignal()

    def __init__(self, rows_and_names, output_dir, parent=None):
        super().__init__(parent)
        self.rows_and_names = rows_and_names  # list of (row, lib_name)
        self.output_dir = output_dir
        self._abort = False

    # --- Public Functions ---
    def abort(self) -> None:
        """Signals the worker to abort downloading."""
        self._abort = True

    def run(self) -> None:
        """Downloads the gene set libraries.

        Emits signals when starting and finishing each library, and when all are done.
        """
        base_url = "https://maayanlab.cloud/Enrichr/geneSetLibrary?mode=text&libraryName="
        # Ensure directory
        try:
            os.makedirs(self.output_dir, exist_ok=True)
        except Exception:
            pass

        for row, lib_name in self.rows_and_names:
            if self._abort:
                break
            self.started_library.emit(row, lib_name)

            try:
                encoded = quote(lib_name)
                url = f"{base_url}{encoded}"
                resp = requests.get(url, timeout=60)
                resp.raise_for_status()

                out_path = os.path.join(self.output_dir, f"{lib_name}.gmt")
                with open(out_path, "w", encoding="utf-8") as fh:
                    fh.write(resp.text)

                success = True
            except Exception:
                success = False

            self.finished_library.emit(row, lib_name, success)

        self.all_done.emit()
