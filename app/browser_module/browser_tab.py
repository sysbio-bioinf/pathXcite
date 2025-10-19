"""A single browser tab using QWebEngineView with ID extraction capabilities"""
# --- Standard Library Imports ---
import os
import re
import weakref
from typing import Any

# --- Third Party Imports ---
from PyQt5 import sip
from PyQt5.QtCore import QTimer, QUrl
from PyQt5.QtGui import QGuiApplication
from PyQt5.QtWebEngineWidgets import QWebEnginePage, QWebEngineView
from PyQt5.QtWidgets import QMenu

# Disable sandboxing for WebEngine (needed on some systems)
os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"

# --- Constants ---
TAB_URLS = {
    "PubTator": "https://www.ncbi.nlm.nih.gov/research/pubtator/",
    "PubMed": "https://pubmed.ncbi.nlm.nih.gov",
    "NCBI Gene": "https://www.ncbi.nlm.nih.gov/gene/",
    "PMC": "https://www.ncbi.nlm.nih.gov/pmc/",
    "Web Browser": "https://www.google.com"
}


# --- Public Classes ---
class BrowserTab(QWebEngineView):
    """A single browser tab with ID extraction capabilities."""

    def __init__(self, url: str, browser_view: Any, name: str = None):
        """
        Initialize a browser tab.

        Args:
            url (str): Initial URL to load.
            browser_view (WebBrowser): Reference to the parent browser view.
            name (str, optional): Name of the tab. Defaults to None.
        """

        super().__init__()
        self.browser_view: Any = browser_view
        self.name = name or "Browser Tab"

        # ask the app for a page PARENTED TO THIS VIEW
        self.setPage(browser_view.main_app.get_new_web_page(parent=self))

        self.zoom_factor = 0.7
        self.setZoomFactor(self.zoom_factor)
        self.pmids, self.pmcids = set(), set()

        if url:
            self.setUrl(QUrl(url))
        self.loadFinished.connect(self.on_load_finished)

    # -- Public Methods ---
    def get_current_name(self) -> str | None:
        """Determine the current site name based on the URL."""
        # If the wrapped C++ object is gone, bail out
        if sip.isdeleted(self):
            return None

        u = self.url().toString() if self.url() else ""
        if "pmc.ncbi.nlm.nih.gov" in u or "ncbi.nlm.nih.gov/pmc" in u:
            return "PMC"
        elif "pubmed.ncbi.nlm.nih.gov" in u:
            return "PubMed"
        elif "www.ncbi.nlm.nih.gov/" in u and "pubtator3" in u:
            return "PubTator"
        elif u.startswith("https://www.google.com"):
            return "Web Browser"
        return None

    def context_menu_event(self, event: Any) -> None:
        """Custom context menu for the browser tab.

        Args:
            event: The context menu event.

        Returns:
            None
        """
        page: QWebEnginePage = self.page()
        if page is None:
            return

        data: QWebEnginePage.ContextMenuData = page.contextMenuData()
        menu = QMenu(self)

        menu.addAction(page.action(QWebEnginePage.Back))
        menu.addAction(page.action(QWebEnginePage.Forward))
        menu.addAction(page.action(QWebEnginePage.Reload))
        menu.addSeparator()

        menu.addAction(page.action(QWebEnginePage.SavePage))

        url: QUrl = data.linkUrl()
        if url.isValid():
            url_str = url.toString()

            def open_in_new_tab():
                self.browser_view.add_new_tab(url=url_str, switch_to=True)

            menu.addAction("Open link in new tab", open_in_new_tab)

            def copy_link():
                QGuiApplication.clipboard().setText(url_str)
            menu.addAction("Copy link address", copy_link)

        # If text is selected, add "Add Bookmark"
        if data.selectedText():
            def add_bookmark():
                pass  # TODO: implement bookmark addition logic

            menu.addSeparator()
            menu.addAction("Add Bookmark", add_bookmark)

        menu.exec_(event.globalPos())

    def navigate(self, url: str) -> None:
        """Navigate to a specified URL."""
        self.setUrl(QUrl(url))

    def zoom_in(self) -> None:
        """Zoom in the current page."""
        self.zoom_factor += 0.1
        self.setZoomFactor(self.zoom_factor)

    def zoom_out(self) -> None:
        """Zoom out the current page."""
        self.zoom_factor = max(0.1, self.zoom_factor - 0.1)
        self.setZoomFactor(self.zoom_factor)

    def reset_zoom(self) -> None:
        """Reset zoom to default."""
        self.zoom_factor = 1.0
        self.setZoomFactor(self.zoom_factor)

    def set_zoom_factor(self, value: float) -> None:
        """Set zoom factor to a specific value."""
        self.zoom_factor = value / 100
        self.setZoomFactor(self.zoom_factor)

    def find_on_page(self, text: str) -> None:
        """Find text on the current page."""
        self.findText("", QWebEnginePage.FindFlags())  # Clear previous
        if text:
            self.findText(text, QWebEnginePage.FindFlags())

    def extract_ids(self, callback=None) -> None:
        """Extract PubMed and PMC IDs from the current page's HTML content.

        Args:
            callback: Function to call with extracted IDs. Defaults to None.

        Returns:
            None
        """
        # Weak reference so one can tell if the tab died before the callback runs
        view_ref = weakref.ref(self)

        page: QWebEnginePage = self.page()
        # If the page/view is already gone, do nothing
        if page is None or sip.isdeleted(self):
            return

        def handle_html(html: str) -> None:
            """Handle the HTML content to extract IDs."""
            view = view_ref()
            # If the tab was closed meanwhile, abort
            if view is None or sip.isdeleted(view):
                return

            pmcids, pmids = set(), set()
            name = view.get_current_name() or "Unknown"

            if name == "PubTator":
                pmid_pattern = re.compile(r'PMID\d{6,10}', re.IGNORECASE)
                pmids = set(pmid_pattern.findall(html))

            elif name == "PubMed":
                scan_pmid_p = r'<span[^>]+class="docsum-pmid"[^>]*>\s*(\d{6,10})\s*</span>'
                span_pmid_pattern = re.compile(scan_pmid_p,
                                               re.IGNORECASE)
                strong_pmid_p = r'<strong[^>]+class="current-id"[^>]*title="PubMed ID"[^>]*>\s*(\d{6,10})\s*</strong>'
                strong_pmid_pattern = re.compile(strong_pmid_p,
                                                 re.IGNORECASE)
                pmcid_link_p = r'<a[^>]+href="https?://www\.ncbi\.nlm\.nih\.gov/pmc/articles/(PMC\d{6,10})/"'
                pmcid_link_pattern = re.compile(pmcid_link_p,
                                                re.IGNORECASE)

                pmids.update(span_pmid_pattern.findall(html))
                pmids.update(strong_pmid_pattern.findall(html))
                pmcids.update(pmcid_link_pattern.findall(html))

            elif name == "PMC":
                pmcid_pattern = re.compile(r'\b(PMC\d{6,10})\b', re.IGNORECASE)
                pmid_link_pattern = re.compile(r'href=["\']https://pubmed\.ncbi\.nlm\.nih\.gov/(\d{6,10})/?["\']',
                                               re.IGNORECASE)
                pmcids.update(pmcid_pattern.findall(html))
                pmids.update(pmid_link_pattern.findall(html))

            else:
                pmcid_pattern = re.compile(
                    r'\b(?:PMCID:?\s*)?(PMC\d{6,10})\b', re.IGNORECASE)
                pmid_pattern = re.compile(
                    r'\b(?:PMID:?\s*)?(\d{6,10})\b', re.IGNORECASE)
                pmcids = set(pmcid_pattern.findall(html))
                pmids = set(pmid_pattern.findall(html))
                pmids = {pid for pid in pmids if not any(
                    pid in pmc for pmc in pmcids)}

            # Re-check before touching attributes
            if view is None or sip.isdeleted(view):
                return

            view.pmids = pmids
            view.pmcids = pmcids

            if callback:
                callback(pmids, pmcids)

        try:
            page.toHtml(handle_html)

        except RuntimeError:
            # If the page gets torn down during call setup
            pass

    def on_title_changed(self, title: str) -> None:
        """Update the tab label based on the current page title and known site."""
        idx = self.browser_view.tabs.indexOf(self)
        if idx == -1:
            return
        site: str | None = self.get_current_name()
        if site in ("PubTator", "PubMed", "PMC"):
            self.browser_view.tabs.setTabText(idx, site)
        else:
            self.browser_view.tabs.setTabText(idx, title or "Untitled")

    def on_load_finished(self, ok: bool) -> None:
        """Handle actions after the page has finished loading."""
        if ok:
            # only scan the CURRENT tab
            is_automatic = self.browser_view.get_scan_automatically()
            is_current = self.browser_view.tabs.currentWidget() is self
            if is_automatic and is_current:
                QTimer.singleShot(5000, self.browser_view.scan_current_tab_ids)
