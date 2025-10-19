"""Worker for running enrichment analysis in a separate thread"""

# --- Standard Library Imports ---
import time

# --- Third Party Imports ---
from PyQt5.QtCore import QMutex, QRunnable, QWaitCondition

# --- Local Imports ---
from app.workers.signals import WorkerSignals

# --- Public Classes ---


class EnrichmentWorker(QRunnable):
    """Worker for running EnrichmentAnalysis in a separate thread."""

    def __init__(self, main_app, process_manager, task_name, enrichment_analysis_process):
        super().__init__()
        self.main_app = main_app
        self.process_manager = process_manager
        self.task_name = task_name
        self.enrichment_analysis_process = enrichment_analysis_process

        self.signals = WorkerSignals()

        # control
        self.is_running = True
        self.is_paused = False
        self.mutex = QMutex()
        self.pause_condition = QWaitCondition()

        self.results_df = None

    # --- Public Functions ---
    def run(self):
        """Runs the enrichment process asynchronously (only processing; UI via signals)."""
        try:
            self.signals.progress.emit(self.task_name, 30)

            for attempt in range(1, self.enrichment_analysis_process.max_retries + 1):
                if not self.is_running:
                    return

                self.mutex.lock()
                while self.is_paused:
                    self.pause_condition.wait(self.mutex)
                self.mutex.unlock()

                try:
                    self.results_df = self.enrichment_analysis_process.perform_pea()
                    break
                except Exception as e:
                    if attempt < self.enrichment_analysis_process.max_retries:
                        time.sleep(
                            self.enrichment_analysis_process.retry_delay)
                    else:
                        self.signals.error.emit(self.task_name, str(e))
                        return

            if self.results_df is not None and not self.results_df.empty:
                self.signals.progress.emit(self.task_name, 70)
                self.signals.ui_update.emit(self.task_name, self.results_df)

            self.signals.progress.emit(self.task_name, 100)
            self.signals.finished.emit(self.task_name, self.results_df)

        except Exception as e:
            self.signals.error.emit(self.task_name, str(e))
        finally:
            self.process_manager.stop_task(self.task_name)

    # controls
    def pause(self):
        """Pause the worker."""
        self.is_paused = True

    def resume(self):
        """Resume the worker."""
        self.is_paused = False
        self.mutex.lock()
        self.pause_condition.wakeAll()
        self.mutex.unlock()

    def stop(self):
        """Stop the worker."""
        self.is_running = False
        self.resume()

    def set_progress(self, progress):
        """Set the progress of the worker."""
        self.mutex.lock()
        try:
            pass  # TODO

        finally:
            self.mutex.unlock()

    def set_name(self, task_name):
        """Set the task name."""
        self.task_name = task_name
