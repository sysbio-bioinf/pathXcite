"""Worker for retrieving articles by IDs and adding them to the database"""

# --- Standard Library Imports ---
import sys
import traceback

# --- Third Party Imports ---
from PyQt5.QtCore import QRunnable

# --- Local Imports ---
from app.workers.signals import WorkerSignals

# --- Public Classes ---


class ArticleRetrievalWorker(QRunnable):
    """Worker to retrieve articles by IDs and add them to the database."""

    def __init__(self, main_app, process_manager, task_name, selected_ids, db_path,
                 email=None, api_key=None):
        super().__init__()
        self.main_app = main_app
        self.process_manager = process_manager
        self.task_name = task_name
        self.selected_ids = selected_ids
        self.db_path = db_path
        self.email = email
        self.api_key = api_key

        self.signals = WorkerSignals()

    # --- Public Functions ---
    def run(self):
        """Retrieve articles by IDs and add them to the database."""
        try:
            from app.database.database_update import add_articles_to_db

            pmids = self.selected_ids.get("pmids", []) or []
            pmcids = self.selected_ids.get("pmcids", []) or []
            if not pmids and not pmcids:
                raise ValueError("No IDs provided to retrieve.")

            # Perform retrieval + DB insert
            add_articles_to_db(self.main_app, pmids + pmcids,
                               self.db_path, email=self.email, api_key=self.api_key)

            # Notify to refresh anything dependent on the DB
            self.signals.ui_update.emit(self.task_name, None)

            # Use unified finished signature (task_id, payload)
            self.signals.finished.emit(self.task_name, None)

        except Exception as e:
            tb_str = "".join(traceback.format_exception(*sys.exc_info()))
            self.signals.error.emit(self.task_name, f"{e}\n{tb_str}")
