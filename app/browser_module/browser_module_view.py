"""The main web browser view for the browser module, with tabbed browsing and article ID scanning"""

# --- Standard Library Imports ---
import os
from typing import Any

# --- Third Party Imports ---
from PyQt5.QtCore import Qt, QTimer, QUrl
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLineEdit,
    QSizePolicy,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)

# --- Local Imports ---
from app.browser_module.browser_tab import BrowserTab
from app.util_widgets.clickable_widget import IconTextButton, IconTextLabel
from app.util_widgets.custom_spin_box import CustomSpinBox
from app.util_widgets.dropdown import DropdownToolButton
from app.util_widgets.icon_line_edit import IconLineEdit
from app.util_widgets.svg_button import SvgButton, SvgHoverButton, SvgToggleButton

# --- Disable sandboxing for Qt WebEngine ---
# Disable sandboxing for Qt WebEngine (if needed)
os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"

# --- Constants ---
# Predefined URLs for common tabs
TAB_URLS = {
    "PubTator": "https://www.ncbi.nlm.nih.gov/research/pubtator/",
    "PubMed": "https://pubmed.ncbi.nlm.nih.gov",
    "NCBI Gene": "https://www.ncbi.nlm.nih.gov/gene/",
    "PMC": "https://www.ncbi.nlm.nih.gov/pmc/",
    "Web Browser": "https://www.google.com"
}

# --- Public Classes ---


class WebBrowser(QSplitter):
    """ Main web browser view with tabbed browsing and article ID scanning. """

    def __init__(self, main_app: Any, browser_settings_view: Any):
        """ 
        Main web browser view with tabbed browsing and article ID scanning.

        Args:
            main_app: Main application instance for interaction.
            browser_settings_view: The browser settings panel to show alongside the browser.
        """

        super().__init__()
        self.main_app = main_app
        self.browser_settings_view = browser_settings_view
        self.toolbar_actions: list[QWidgetAction] = []
        self.toolbar_actions2: list[QWidgetAction] = []

        self.web_toolbar = QWidget()
        self.web_toolbar_layout = QHBoxLayout(self.web_toolbar)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self._close_tab)

        self.scan_result_pmids: list[str] = []
        self.scan_result_pmcids: list[str] = []
        self.is_initialized: bool = False

        self._init_ui()
        self._init_toolbar_actions()


    # --- Public Methods ---
    def refresh_current_tab(self) -> None:
        """Reload the current tab."""
        current_widget = self.tabs.currentWidget()
        if hasattr(current_widget, "reload"):
            current_widget.reload()
        self._update_nav_buttons()
        if self.get_scan_automatically():
            QTimer.singleShot(5000, self.scan_current_tab_ids)

    def on_tab_url_changed(self, url: QUrl, tab: BrowserTab) -> None:
        """
        Handle URL changes in a tab to update tab label and URL bar.

        Args:
            url: The new URL of the tab.
            tab: The BrowserTab instance that changed.

        Returns:
            None
        """
        site = tab.get_current_name()
        idx = self.tabs.indexOf(tab)
        if idx != -1:
            if site in ("PubTator", "PubMed", "PMC"):
                self.tabs.setTabText(idx, site)
            else:
                # Use whatever title we have now; the titleChanged signal will refine it if needed.
                self.tabs.setTabText(idx, tab.title() or "Loading…")
        if self.tabs.currentWidget() == tab:
            self.url_bar.setText(url.toString())
            if self.get_scan_automatically():
                QTimer.singleShot(5000, self.scan_current_tab_ids)
        self._update_nav_buttons()

    def get_scan_results(self) -> dict[str, list[str]]:
        """
        Return the results of the last scan as a dictionary.

        Args:
            None

        Returns:
            dict: A dictionary with keys "pmids" and "pmcids" containing lists of scanned IDs.
        """
        return {
            "pmids": self.scan_result_pmids,
            "pmcids": self.scan_result_pmcids
        }

    def get_scan_behavior(self) -> str:
        """
        Return the current scan behavior.

        Args:
            None

        Returns:
            str: The selected scan behavior ("Scan & Append" or "Scan & Replace").
        """
        return self.scan_behavior_combobox.currentText()

    def update_url_bar(self, url: QUrl) -> None:
        """
        Update the URL bar to reflect the current tab's URL.

        Args:
            url: The new URL to display.

        Returns:
            None
        """
        self.url_bar.setText(url.toString())
        
    def add_new_gene_info_tab(self, gene_id: str | None, switch_to: bool = True) -> BrowserTab:
        """
        Create a new tab for NCBI Gene; if gene_id is None, open the main Gene page.

        Args:
            gene_id: The gene ID to open. If None, opens the main Gene page.
            switch_to: Whether to switch to the new tab immediately. Defaults to True.

        Returns:
            BrowserTab: The newly created browser tab.
        """
        if gene_id:
            url = f"https://www.ncbi.nlm.nih.gov/gene/{gene_id}"
        else:
            url = "https://www.ncbi.nlm.nih.gov/gene/"
        tab = BrowserTab(url, self, "NCBI Gene")
        idx = self.tabs.addTab(tab, "NCBI Gene")
        tab.urlChanged.connect(lambda u, t=tab: self.on_tab_url_changed(u, t))
        if switch_to:
            self.tabs.setCurrentIndex(idx)
        # trigger initial sync
        self._sync_url_bar(self.tabs.currentIndex())
        return tab

    def add_new_article_info_tab(self, article_id: str | None,
                                 db_name: str = "", switch_to: bool = True) -> BrowserTab:
        """
        Create a new tab for NCBI Article; if article_id is None, open the main Article page.

        Args:
            article_id: The article ID (PMID or PMCID) to open.If None, opens the main Article page.
            db_name: The database name ("PubMed" or "PMC").
            switch_to: Whether to switch to the new tab immediately. Defaults to True.

        Returns:
            BrowserTab: The newly created browser tab.
        """
        url = "https://pubmed.ncbi.nlm.nih.gov/"
        if article_id:
            if db_name == "PubMed":
                url = f"https://pubmed.ncbi.nlm.nih.gov/{article_id}/"
            elif db_name == "PMC":
                url = f"https://pmc.ncbi.nlm.nih.gov/articles/{article_id}/"

        tabname = "NCBI Article"
        if db_name:
            tabname = f"{db_name}: {article_id}"
        tab = BrowserTab(url, self, tabname)
        idx = self.tabs.addTab(tab, tabname)
        tab.urlChanged.connect(lambda u, t=tab: self.on_tab_url_changed(u, t))
        if switch_to:
            self.tabs.setCurrentIndex(idx)
        # trigger initial sync
        self._sync_url_bar(self.tabs.currentIndex())
        return tab

    def get_scan_automatically(self) -> bool:
        """
        Return whether automatic scanning is enabled.

        Args:
            None

        Returns:
            bool: True if automatic scanning is enabled, False otherwise.
            """
        return self.scan_automatically_checkbox.isChecked()

    def scan_current_tab_ids(self) -> None:
        """Scan the current tab for article IDs and update the main app."""
        current_widget = self.tabs.currentWidget()
        if not isinstance(current_widget, BrowserTab):
            print("No valid tab selected or not a BrowserTab instance.")
            return

        def after_extract(pmids, pmcids):
            pmids = set(pmids)
            pmcids = set(pmcids)

            self.scan_result_pmids = pmids
            self.scan_result_pmcids = pmcids

            if self.main_app:
                # {"pmids": [...], "pmcids": [...]}
                all_db_ids = self.main_app.get_db_ids()
                db_pmids = all_db_ids.get("pmids", [])
                db_pmcids = all_db_ids.get("pmcids", [])

                # do case-insensitive match safely
                pmids_lc = {p.lower() for p in pmids}
                pmcids_lc = {p.lower() for p in pmcids}

                saved_ids = db_pmcids + db_pmids
                saved_ids = [
                    _id for _id in saved_ids
                    if _id.lower() in pmids_lc or _id.lower() in pmcids_lc
                ]

                self.main_app.update_browser_settings(
                    {"pmids": pmids, "pmcids": pmcids},
                    self.get_scan_behavior(),
                    saved_ids
                )

        current_widget.extract_ids(callback=after_extract)


    # --- Private Methods ---
    def _add_new_tab(self, url: str | None = None, switch_to: bool = True) -> BrowserTab:
        """
        Always create a new tab with PMC by default; user can change the URL later.

        Args:
            url: The URL to open in the new tab. If None, opens the default PMC page.
            switch_to: Whether to switch to the new tab immediately. Defaults to True.

        Returns:
            BrowserTab: The newly created browser tab.
        """
        title = "PMC"
        if url is not None:
            title = url
        if title in TAB_URLS:
            start_url = TAB_URLS[title]
        else:
            start_url = url
        tab = BrowserTab(start_url, self, title)
        idx = self.tabs.addTab(tab, title)
        tab.urlChanged.connect(lambda u, t=tab: self.on_tab_url_changed(u, t))
        if switch_to:
            self.tabs.setCurrentIndex(idx)
        # trigger initial sync
        self._sync_url_bar(self.tabs.currentIndex())
        return tab

    def _close_tab(self, index: int) -> None:
        """
        Close the tab at the given index, cleaning up signals.

        Args:
            index: The index of the tab to close.

        Returns:
            None
        """
        if self.tabs.count() <= 1:
            return
        tab = self.tabs.widget(index)
        if isinstance(tab, BrowserTab):
            for sig, slot in (
                (tab.loadFinished, tab.on_load_finished),
                (tab.titleChanged, getattr(tab, "on_title_changed", None)),
            ):
                try:
                    if slot is not None:
                        sig.disconnect(slot)
                except TypeError:
                    pass
        self.tabs.removeTab(index)
        tab.deleteLater()
        self._sync_url_bar(self.tabs.currentIndex())

    def _init_toolbar_actions(self) -> None:
        """Initialize toolbar actions and widgets.
        Args:
            None
        Returns:
            None
        """
        def make_vstretch():
            s = QWidget()
            # stretch vertically; don't greedily take horizontal space
            s.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
            return s

        self.scan_panel = IconTextButton("Scan For Articles", "scan_white",
                                         "Scan only the CURRENT tab for article IDs",
                                         20, lambda: self.scan_current_tab_ids())
        self.scan_panel.setFixedWidth(150)
        self.zoom_panel = IconTextLabel(
            "Page Zoom", None, "Zoom in/out of current page", 20)

        self.zoom_spin = CustomSpinBox(
            number_change_fct=self._set_zoom, parent=self)

        vline = QFrame()
        vline.setFrameShape(QFrame.VLine)
        vline.setFrameShadow(QFrame.Sunken)
        self.zoom_panel.get_layout().addWidget(vline)
        self.zoom_panel.get_layout().addWidget(self.zoom_spin)

        self.back_button = SvgHoverButton(
            "back",
            tooltip="Navigate back",
            triggered_func=lambda: self._navigate_back(),
            width=24, height=24
        )

        self.forward_button = SvgHoverButton(
            "forward",
            tooltip="Navigate forward",
            triggered_func=lambda: self._navigate_forward(),
            width=24, height=24
        )

        # New Tab (+) -> always PMC
        self.new_tab_button = SvgHoverButton(
            "add_tab",
            tooltip="New Tab",
            triggered_func=lambda: self._add_new_tab(),
            width=24, height=24
        )

        self.refresh_button = SvgHoverButton(
            "reload2",
            tooltip="Reload Tab",
            triggered_func=lambda: self.refresh_current_tab(),
            width=24, height=24
        )

        options = {
            "PubMed": lambda: self.url_bar.setText(TAB_URLS.get("PubMed", "")),
            "PubMed Central": lambda: self.url_bar.setText(TAB_URLS.get("PMC", "")),
        }

        s_widget = SvgHoverButton(
            "NIH", tooltip=None, triggered_func=None, width=55, height=24)
        website_dropdown = DropdownToolButton(
            base_text="",
            options=options,
            button=s_widget,
            collapsed_visual=lambda b: getattr(b, "setBaseName")("NIH"),
            expanded_visual=lambda b: getattr(b, "setBaseName")("NIH2"),
        )
        website_dropdown.optionTriggered.connect(lambda t: self._set_url(t))

        self.url_bar = IconLineEdit("search", tooltip="Enter URL",
                                    on_click=self._load_free_browsing_url, icon_size=22,
                                    icon_position="right")

        self.url_bar.setPlaceholderText("Enter URL...")
        # self.url_bar.returnPressed.connect(self._load_free_browsing_url)
        self.url_bar.setFixedHeight(32)
        self.url_bar.setMinimumWidth(400)

        self.find_button = SvgToggleButton(
            "find",
            tooltip="Show/Hide the Find tool bar",
            show_func=self._toggle_search_bar,
            collapse_func=lambda: self._toggle_search_bar(),
            size=24,
            width=45,
            height=30,
            initial_action="show",  # or "collapse"
        )

        # Wrap each widget in a QWidgetAction so TopBar can render them
        def wrap(widget):
            act = QWidgetAction(self)
            act.setDefaultWidget(widget)
            return act

        self.toolbar_actions.extend([
            wrap(self.new_tab_button),
            wrap(website_dropdown),
            wrap(self.back_button),
            wrap(self.forward_button),
            wrap(self.url_bar),
            wrap(self.refresh_button)
        ])

        self.toolbar_actions2.extend([
            wrap(self.zoom_panel),
            wrap(make_vstretch()),
            wrap(self.scan_panel),
            wrap(self.scan_automatically_checkbox),
            wrap(self.scan_behavior_combobox),
            wrap(self.find_button)
        ])

    def _set_url(self, t: str) -> None:
        """
        Set the URL bar to the selected tab URL.

        Args:
            t: The tab name selected ("PubMed" or "PubMed Central").

        Returns:
            None
        """
        if t == "PubMed Central":
            t = "PMC"
        url = TAB_URLS.get(t, "")

        self.url_bar.setText(url)
        self._load_free_browsing_url()

    def _init_ui(self) -> None:
        """Initialize the main UI layout."""
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)

        sidebar_layout = QVBoxLayout()
        sidebar_layout.setAlignment(Qt.AlignTop)

        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)

        top_bar_layout = QHBoxLayout()

        # Basic top bar controls (unused layout retained for compatibility)
        self.back_button = SvgButton(
            svg_file_name="back.svg",
            tooltip="Back",
            triggered_func=lambda: self._navigate_back(),
            size=24
        )
        self.forward_button = SvgButton(
            svg_file_name="forward.svg",
            tooltip="Forward",
            triggered_func=lambda: self._navigate_forward(),
            size=24
        )

        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("Enter URL...")
        self.url_bar.returnPressed.connect(self._load_free_browsing_url)
        self.url_bar.setFixedHeight(32)

        self.refresh_button = SvgButton(
            svg_file_name="reload.svg",
            tooltip="Refresh current page",
            triggered_func=lambda: self.refresh_current_tab(),
            size=24
        )

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search on page...")
        self.search_bar.returnPressed.connect(self._search_on_page)
        self.search_bar.setFixedHeight(28)
        self.search_bar.setVisible(False)

        self.scan_automatically_checkbox = QCheckBox("Auto-scan current tab")
        self.scan_automatically_checkbox.setChecked(False)
        self.scan_behavior_combobox = QComboBox()
        self.scan_behavior_combobox.addItems(
            ["Scan & Append", "Scan & Replace"])

        content_layout.addLayout(top_bar_layout)
        content_layout.addWidget(self.search_bar)
        content_layout.addWidget(self.tabs)

        main_layout.addLayout(sidebar_layout)
        main_layout.addLayout(content_layout)

        # Start with a single PMC tab
        self._add_new_tab(url=TAB_URLS["PMC"], switch_to=True)

        self.tabs.currentChanged.connect(self._sync_url_bar)
        self.is_initialized = True

        self.addWidget(main_widget)
        self.addWidget(self.browser_settings_view)
        self.setStretchFactor(0, 3)
        self.setStretchFactor(1, 2)

    def _toggle_search_bar(self) -> None:
        """Show or hide the search bar."""
        is_visible = self.search_bar.isVisible()
        self.search_bar.setVisible(not is_visible)
        if not is_visible:
            self.search_bar.setFocus()

    def _load_free_browsing_url(self) -> None:
        """Load the URL from the URL bar into the current tab."""
        url = self.url_bar.text().strip()
        if not url:
            return
        if not url.startswith("http"):
            url = "https://" + url
        current_widget = self.tabs.currentWidget()
        if isinstance(current_widget, BrowserTab):
            current_widget.navigate(url)

    def _sync_url_bar(self, index: int) -> None:
        """
        Sync the URL bar with the tab at the given index.

        Args:
            index: The index of the tab to sync with.

        Returns:
            None
        """
        current_widget = self.tabs.widget(index)
        if isinstance(current_widget, QWebEngineView):
            self.url_bar.setText(current_widget.url().toString())
        self._update_nav_buttons()
        # scan ONLY current tab after a short delay
        if self.get_scan_automatically():
            QTimer.singleShot(5000, self.scan_current_tab_ids)

    def _update_nav_buttons(self) -> None:
        """Enable or disable navigation buttons based on current tab history."""
        current_widget = self.tabs.currentWidget()
        if isinstance(current_widget, QWebEngineView):
            self.back_button.setEnabled(current_widget.history().canGoBack())
            self.forward_button.setEnabled(
                current_widget.history().canGoForward())

    def _set_zoom(self, zoom_factor: float) -> None:
        """Set the zoom factor for the current tab.

        Args:
            zoom_factor: The zoom factor to set (e.g., 100 for 100%).

        Returns:
            None
        """
        current_widget = self.tabs.currentWidget()
        if isinstance(current_widget, BrowserTab):
            current_widget.set_zoom_factor(zoom_factor)

    def _search_on_page(self) -> None:
        """Search for text on the current page."""
        current_widget = self.tabs.currentWidget()
        if isinstance(current_widget, BrowserTab):
            text = self.search_bar.text().strip()
            current_widget.find_on_page(text)

    def _navigate_back(self) -> None:
        """Navigate back in the current tab's history."""
        current_widget = self.tabs.currentWidget()
        if isinstance(current_widget, QWebEngineView) and current_widget.history().canGoBack():
            current_widget.back()

    def _navigate_forward(self) -> None:
        """Navigate forward in the current tab's history."""
        current_widget = self.tabs.currentWidget()
        if isinstance(current_widget, QWebEngineView) and current_widget.history().canGoForward():
            current_widget.forward()
