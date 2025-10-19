"""Worker to ping NCBI E-utilities API to validate email and API key"""

# --- Standard Library Imports ---
import requests

# -- Third Party Imports ---
from PyQt5.QtCore import QObject, QRegularExpression, pyqtSignal, pyqtSlot

# --- Constants ---
EMAIL_RE = QRegularExpression(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


# -- Public Classes ---
class PingWorker(QObject):
    """Worker to ping NCBI E-utilities API to validate email and API key."""
    finished = pyqtSignal(bool, str)  # (ok, message)

    def __init__(self, email: str, api_key: str | None, timeout: int = 8,
                 tool_name: str = "pathXcite"):
        super().__init__()
        self.email = email
        self.api_key = api_key or None
        self.timeout = timeout
        self.tool_name = tool_name

    @pyqtSlot()
    def run(self):
        """Ping NCBI E-utilities API to validate email and API key."""
        try:
            params = {
                "db": "pubmed",
                "retmode": "json",
                "tool": self.tool_name,
                "email": self.email,
                "term": "brca1[gene] AND human[orgn]",
            }
            if self.api_key:
                params["api_key"] = self.api_key

            headers = {
                "User-Agent": f"{self.tool_name}/1.0 (mailto:{self.email})"}

            url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"

            r = requests.get(url, params=params,
                             headers=headers, timeout=self.timeout)

            r.raise_for_status()

            # JSON check
            try:
                _ = r.json()
            except ValueError:
                print("[PingWorker] WARN: non-JSON response despite retmode=json")

            self.finished.emit(True, "Ping successful")

        except requests.exceptions.HTTPError as e:
            msg = f"Ping failed (HTTP): {e}"
            try:
                msg += f" | {r.text[:200]}..."
            except Exception:
                pass
            print("[PingWorker] ERROR", msg)
            self.finished.emit(False, msg)

        except requests.exceptions.RequestException as e:
            msg = f"Ping failed (network): {e}"
            print("[PingWorker] ERROR", msg)
            self.finished.emit(False, msg)
