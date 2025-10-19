"""Create and manage QWebEngineProfile, Page, and View instances"""

# --- Standard Library Imports ---
import hashlib
import weakref
from pathlib import Path
from typing import Optional

# --- Third Party Imports ---
from PyQt5.QtCore import QCoreApplication, QObject
from PyQt5.QtWebEngineWidgets import QWebEnginePage, QWebEngineProfile, QWebEngineView


# --- Public Classes ---
class QuietPage(QWebEnginePage):
    """A QWebEnginePage that suppresses JavaScript console messages."""

    # --- Public Functions ---
    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        """Override to suppress console messages."""
        return


class WebEngineRegistry(QObject):
    """
    Own 1 shared QWebEngineProfile and provide factories for Page/View
    that all use that profile.
    """

    def __init__(self,
                 app_name: str,
                 project_dir: str,
                 *,
                 parent: Optional[QObject] = None,
                 off_the_record: bool = False,
                 use_default_profile: bool = False):
        super().__init__(parent)
        self._app_name = app_name
        self._project_dir = str(Path(project_dir).expanduser())
        self._off_the_record = off_the_record
        self._use_default_profile = use_default_profile

        self._tracked_pages: "weakref.WeakSet[QWebEnginePage]" = weakref.WeakSet(
        )
        self._tracked_views: "weakref.WeakSet[QWebEngineView]" = weakref.WeakSet(
        )

        self.profile = self._create_profile()   # IMPORTANT: parentless
        self._configure_profile()

    # --- Public Functions ---
    def create_page(self, parent: Optional[QObject] = None) -> QWebEnginePage:
        """Create a QWebEnginePage using the shared profile."""
        page = QuietPage(self.profile, parent)  # give QObject parent
        self._tracked_pages.add(page)
        return page

    def create_view(self, parent: Optional[QObject] = None) -> QWebEngineView:
        """Create a QWebEngineView using a new page with the shared profile."""
        view = QWebEngineView(parent)
        view.setPage(self.create_page(view))  # view owns page
        self._tracked_views.add(view)
        return view

    def attach_to_view(self, view: QWebEngineView) -> QWebEngineView:
        """Attach the shared profile to an existing QWebEngineView."""
        old_url = view.url() if hasattr(view, "url") else None
        view.setPage(self.create_page(view))
        if old_url and old_url.isValid():
            view.setUrl(old_url)
        self._tracked_views.add(view)
        return view

    def shutdown(self, wait_ms: int = 250):
        """
        Delete all views/pages first, THEN release the profile.
        Is called from the main windows closeEvent AFTER deleting the views.
        """
        try:
            # Delete any still-tracked views and pages
            for v in list(self._tracked_views):
                if v:
                    v.deleteLater()
            for p in list(self._tracked_pages):
                if p:
                    p.deleteLater()

            # Let Qt process deletions
            if wait_ms > 0:
                QCoreApplication.processEvents()
        finally:
            try:
                self.profile.deleteLater()
            except Exception:
                pass

    # --- Private Functions ---
    def _create_profile(self) -> QWebEngineProfile:
        """
        Returns a parentless QWebEngineProfile so Qt wont auto-destroy it
        before all pages/views are gone.
        """
        if self._use_default_profile:
            # Default profile is persistent and managed by Qt.
            return QWebEngineProfile.defaultProfile()

        if self._off_the_record:
            return QWebEngineProfile()  # parentless

        # Persistent, project-scoped profile (NAMED + PATHS)
        project_key = hashlib.sha1(
            Path(self._project_dir).resolve().as_posix().encode()
        ).hexdigest()[:10]
        profile_name = f"{self._app_name}-{project_key}"

        base = Path(self._project_dir).resolve() / \
            f".{self._app_name}" / "webengine"
        cache = base / "cache"
        base.mkdir(parents=True, exist_ok=True)
        cache.mkdir(parents=True, exist_ok=True)

        profile = QWebEngineProfile(profile_name)  # parentless
        profile.setPersistentStoragePath(str(base))
        profile.setCachePath(str(cache))
        profile.setPersistentCookiesPolicy(
            QWebEngineProfile.ForcePersistentCookies)

        return profile

    def _configure_profile(self) -> None:
        # TODO
        pass
