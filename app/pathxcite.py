"""Main application class for pathXcite"""

# --- Standard Library Imports ---
import json
import os
import time
from pathlib import Path

# --- Third Party Imports ---
from PyQt5.QtCore import QCoreApplication, Qt, QThreadPool, QTimer
from PyQt5.QtWebEngineWidgets import QWebEnginePage, QWebEngineView
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QMessageBox,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget
)
import pandas as pd

# --- Local Imports ---
from app.bottom_bar.bottom_bar import BottomBar
from app.browser_module.article_id_widget import ArticleIdWidget
from app.browser_module.browser_module_view import WebBrowser
from app.comparison.comparison_module_view import ComparisonModuleView
from app.comparison.interactive_comparison_creation import (
    create_comparison_html,
    validate_tsv_file
)
from app.database.database_creation import create_database
from app.database.database_query import get_all_pubmed_and_pmc_ids
from app.database.database_validation import scan_and_validate_databases
from app.document_insights_module.document_insights_view import DocumentInsightsView
from app.enrichment_module.enrichment_analysis.enrichment_analysis import (
    EnrichmentAnalysis
)
from app.enrichment_module.enrichment_module_view import EnrichmentModuleView
from app.info_panel.info_panel import InfoPanel
from app.logo_bar.logo_bar import LogoBar
from app.menu.sidebar_menu_button import SidebarMenuButton
from app.menu.sidebar_toggle_button import SidebarToggleButton
from app.processes.process_manager import ProcessManager, TaskStatus
from app.processes.task_board import TaskBoardWidget
from app.settings_module.settings_view import SettingsView
from app.top_bar.top_bar import TopBar
from app.utils import get_default_html_svg, resource_path
from app.web_utils.profile_creator import WebEngineRegistry
from app.workers.article_retrieval_worker import ArticleRetrievalWorker
from app.workers.enrichment_worker import EnrichmentWorker


class PathXCite(QWidget):
    """Main application class for pathXcite.

    It manages the UI components, database interactions, and web engine profiles."""

    def __init__(self, folder_path, config_data):
        super().__init__()

        self.folder_path = folder_path
        self.config_data = config_data

        self.api_email = config_data.get("api_email", None)
        self.api_key = config_data.get("api_key", None)

        self.documents_view: QWidget
        self.gene_lists_view: QWidget
        self.valid_databases: dict
        self.num_valid_dbs: int
        self.comparison_html: str
        self.web = WebEngineRegistry(
            app_name="pathXcite",
            project_dir=folder_path,
            parent=self,
            off_the_record=True
        )

        self.process_manager = ProcessManager()
        self._workers_by_task = {}
        # self.enrichment_process_data = {} # TODO: CHECK USAGE

        # Validate and scan databases
        self.db_paths = scan_and_validate_databases(folder_path)

        valid_databases = {}  # TODO: CHECK USAGE
        num_valid_dbs = 0
        for db_path, validation_result in self.db_paths.items():
            if validation_result.get("is_valid", False):
                num_valid_dbs += 1
                valid_databases[db_path] = validation_result.get(
                    "numberArticles", 0)

        try:
            self._init_ui()
            # pause a second to ensure UI is ready
            QTimer.singleShot(1000, self._initialize_databases)

            if isinstance(self.documents_view, DocumentInsightsView):
                if self.documents_view.table_widget is not None:
                    self.documents_view.table_widget.update_db_path(
                        self.top_bar.get_current_database())

            self._update_toolbar(0)
        except Exception as e:
            print(f"Error during initialization: {e}")

    def _init_ui(self):
        """Initialize the main UI components."""
        self.setWindowTitle("PathXCite")
        self.setGeometry(100, 100, 1350, 800)
        self.apply_stylesheet()

        # === Bars ===
        self.logo_bar = LogoBar(self)
        self.top_bar = TopBar(self)
        self.bottom_bar = BottomBar(self)

        # === Main Tab Setup ===
        self.main_tab_widget = QTabWidget()
        self.main_tab_widget.setContentsMargins(0, 0, 0, 0)
        self.main_tab_widget.setTabsClosable(False)
        self.main_tab_widget.tabBar().hide()

        # === Browser View ===
        self.browser_settings_view = ArticleIdWidget(
            self, {"pmids": [], "pmcids": []}, [])
        self.web_browser_view = WebBrowser(self, self.browser_settings_view)

        # === Placeholders for Documents View and Gene Lists View ===
        self.documents_view = QWidget()
        self.gene_lists_view = QWidget()

        # === Settings View ===
        self.configure_settings_view = SettingsView(self, main_app=self,
                                                    assets_path=resource_path(
                                                        "assets"),
                                                    config=self.config_data)

        # === Enrichment Comparison View ===
        self.enrichment_comparison_view = self.get_new_web_view(parent=self)

        icon_path = str(resource_path("assets/icons/load_results.svg"))
        message = "Please select two enrichment results first to view the comparison view."
        default_html = get_default_html_svg(icon_abs_path=icon_path,
                                            width=40,
                                            height=40,
                                            message=message)
        self.enrichment_comparison_view.setHtml(default_html)
        self.comparison_html = default_html

        # === Add Tabs to Main Tab Widget ===
        self.main_tab_widget.addTab(self.web_browser_view, "Web Browser")
        self.main_tab_widget.addTab(self.documents_view, "Document Insights")
        self.main_tab_widget.addTab(self.gene_lists_view, "Enrichment")
        self.main_tab_widget.addTab(
            self.enrichment_comparison_view, "Compare Results")
        self.main_tab_widget.addTab(self.configure_settings_view, "Settings")

        # === Settings Panel ===
        # self.insight_details_view = QWidget()
        # self.comparison_settings_view = QWidget()
        # self.configure_settings_panel = QWidget()

        self.comparison_settings_kit = ComparisonModuleView(self)

        # === Horizontal Splitter (main tabs + settings panel)
        self.right_splitter = QSplitter(Qt.Horizontal)
        self.right_splitter.setContentsMargins(0, 0, 0, 0)
        self.right_splitter.setHandleWidth(1)
        self.right_splitter.addWidget(self.main_tab_widget)

        # === Lower widget (below main content)
        self.task_board = TaskBoardWidget(
            self.process_manager,
            on_cancel=self._cancel_task_clicked,
            on_pause=self._pause_task_clicked,
            on_resume=self._resume_task_clicked
        )

        self.logs_panel = InfoPanel(
            self.folder_path, self, self.task_board, self.process_manager)

        # === Vertical Splitter (upper tabs/settings + lower widget)
        self.middle_splitter = QSplitter(Qt.Vertical)
        self.middle_splitter.setHandleWidth(1)
        self.middle_splitter.addWidget(self.right_splitter)
        self.middle_splitter.addWidget(self.logs_panel)
        self.middle_splitter.setSizes([700, 0])

        # === Sidebar Menu (Collapsible) ===
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(190)
        self.sidebar.setFrameShape(QFrame.StyledPanel)
        self.sidebar.setObjectName("Sidebar")

        sidebar_layout = QVBoxLayout()
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        self.collapse_btn = SidebarToggleButton(
            collapsed=False,
            size=28,
            callback=self._toggle_sidebar
        )

        self.menu_buttons = []
        self.menu_items = [
            ("Web Browser", "web"),
            ("Document Insights", "docs2"),
            ("Enrichment", "pea"),
            ("Compare Results", "compare4"),
            ("Settings", "settings"),
        ]

        self.sidebar_button_container = QWidget()
        sidebar_layout_inner = QVBoxLayout(self.sidebar_button_container)
        sidebar_layout_inner.setContentsMargins(0, 0, 0, 0)
        sidebar_layout_inner.setSpacing(0)

        for i, (label, icon_base) in enumerate(self.menu_items):
            button = SidebarMenuButton(
                icon_base=icon_base,
                text=label,
                size=28,
                index=i,
                callback=self._menu_button_clicked
            )
            self.menu_buttons.append(button)
            sidebar_layout_inner.addWidget(button)

        sidebar_layout_inner.addStretch()
        sidebar_layout.addWidget(self.collapse_btn, alignment=Qt.AlignLeft)
        sidebar_layout.addWidget(self.sidebar_button_container)
        sidebar_layout.addStretch()

        self.sidebar.setLayout(sidebar_layout)

        # === Right side content (TopBar above middle_splitter)
        right_content_layout = QVBoxLayout()
        right_content_layout.setContentsMargins(0, 0, 0, 0)
        right_content_layout.setSpacing(0)
        right_content_layout.addWidget(self.top_bar)
        right_content_layout.addWidget(self.middle_splitter)

        right_content_widget = QWidget()
        right_content_widget.setLayout(right_content_layout)

        # === Horizontal Layout (Sidebar + Right Content)
        center_layout = QHBoxLayout()
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)
        center_layout.addWidget(self.sidebar)
        center_layout.addWidget(right_content_widget)

        center_widget = QWidget()
        center_widget.setLayout(center_layout)

        # === Final Main Layout (Logo + center + bottom)
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(2, 2, 2, 2)
        main_layout.setSpacing(0)
        main_layout.addWidget(self.logo_bar)
        main_layout.addWidget(center_widget)
        main_layout.addWidget(self.bottom_bar)

        self.setLayout(main_layout)

        # === Signal & Initial State
        self.main_tab_widget.currentChanged.connect(
            self._update_settings_panel)

    # main_app
    def get_new_web_page(self, parent=None) -> QWebEnginePage:
        """Create a new QWebEnginePage with the app's web engine profile.

        Returns:
            QWebEnginePage: A new QWebEnginePage instance.
        """
        return self.web.create_page(parent=parent)

    def get_new_web_view(self, parent=None) -> QWebEngineView:
        """Create a new QWebEngineView with the app's web engine profile.

        Returns:
            QWebEngineView: A new QWebEngineView instance.
        """
        return self.web.create_view(parent=parent)

    # === Initialization === #
    def _initialize_databases(self):
        """Initialize database dropdown and ensure at least one valid database exists.
        """
        self._scan_and_validate()

        # If no valid databases exist, prompt user to create one
        while self.num_valid_dbs == 0:
            QMessageBox.warning(self, "No Valid Databases",
                                "There are no valid databases available.")

            # Prompt user for a new database name
            db_name, ok = QInputDialog.getText(
                self, "Create New Database", "Enter a new database name:")

            if not ok or not db_name.strip():
                QMessageBox.critical(
                    self, "Operation Cancelled", "No valid database found or created. Exiting.")
                self.close()
                return

            db_filename = f"{db_name.strip()}.db"
            db_path = os.path.join(self.folder_path, db_filename)

            if os.path.exists(db_path):
                QMessageBox.warning(
                    self, "Database Exists",
                    f"The database '{db_filename}' already exists. Please choose a different name.")
                continue  # Ask again
            else:
                # Create the database
                create_database(db_path)

                # Rescan and revalidate
                self._scan_and_validate()

        self._initialize_dropdown()
        self._init_document_insights_view()

    def _init_document_insights_view(self) -> None:
        """Initialize the Document Insights view."""
        new_documents_view = DocumentInsightsView(
            self, self.top_bar.get_current_database())
        # Remove the placeholder first
        self.main_tab_widget.removeTab(1)

        self.main_tab_widget.insertTab(
            1, new_documents_view, "Document Insights")
        self.documents_view = new_documents_view  # keep reference

        self.main_tab_widget.setCurrentIndex(0)

    def _init_enrichment_module_view(self) -> None:
        """Initialize the Enrichment Module view."""
        new_gene_lists_view = EnrichmentModuleView(self)

        self.main_tab_widget.removeTab(2)

        self.main_tab_widget.insertTab(2, new_gene_lists_view, "Enrichment")

        self.gene_lists_view = new_gene_lists_view

        # Set the current index to the EnrichmentModuleView
        self.main_tab_widget.setCurrentIndex(0)

    def update_config(self, config: dict) -> None:
        """Update the configuration data and rewrite to file.

        Args:
            config (dict): The new configuration data.
        """
        self.config_data = config
        self.api_key = config.get("api_key", None)
        self.api_email = config.get("api_email", None)

        # rewrite to file
        config_file_path = os.path.join(self.folder_path, "config.json")
        with open(config_file_path, "w", encoding="utf-8") as f:
            json.dump(self.config_data, f, indent=4)

    def _initialize_dropdown(self) -> None:
        """Initialize the database dropdown in the top bar."""
        database_paths = sorted(list(self.valid_databases.keys()))
        self.top_bar.set_database_list(database_paths)
        QApplication.processEvents()  # let Qt update UI

        if database_paths:
            first_db_name = Path(database_paths[0]).name
            self.top_bar.update_current_database(first_db_name)

    # === Scan and Validate Databases === #
    def _scan_and_validate(self) -> None:
        """Scan and validate databases in the folder path."""
        self.db_paths = scan_and_validate_databases(self.folder_path)
        self.valid_databases = {}
        self.num_valid_dbs = 0

        for db_path, validation_result in self.db_paths.items():
            if validation_result.get("is_valid", False):
                self.num_valid_dbs += 1
                self.valid_databases[db_path] = validation_result.get(
                    "numberArticles", 0)

    # === Database Utils === #
    def add_new_database(self) -> None:
        """Prompt user to create a new database."""
        db_name, ok = QInputDialog.getText(
            self, "Create New Database", "Enter a new database name:")
        if ok and db_name.strip():
            db_filename = f"{db_name.strip()}.db"
            db_path = os.path.join(self.folder_path, db_filename)

            if os.path.exists(db_path):
                message = f"The database '{db_filename}' already exists. Please choose a different name."
                QMessageBox.warning(self, "Database Exists", message)
            else:
                create_database(db_path)
                time.sleep(0.5)
                self._scan_and_validate()
                self.top_bar.update_dropdown(self.valid_databases, db_filename)

                QMessageBox.information(self, "Database Created",
                                        f"Database '{db_filename}' created successfully.")
        else:
            QMessageBox.warning(self, "Operation Cancelled",
                                "No valid database name provided. Operation cancelled.")

        self.top_bar.add_new_db_button.make_inactive()

    def get_current_database(self) -> str:
        """Get the file path of the currently selected database.

        Returns:
            str: The file path of the currently selected database.
        """
        return self.top_bar.get_current_database()

    def get_db_ids(self) -> dict:
        """Get the IDs from the current database.

        Returns:
            dict: A dictionary containing "pmids" and "pmcids" lists.
        """
        db_path = self.get_current_database()
        if not db_path:
            return {"pmids": [], "pmcids": []}

        id_tuples = get_all_pubmed_and_pmc_ids(db_path)
        pmids = [id_tuple[0]
                 for id_tuple in id_tuples if id_tuple[0] is not None]
        pmcids = [id_tuple[1]
                  for id_tuple in id_tuples if id_tuple[1] is not None]
        return {"pmids": pmids, "pmcids": pmcids}

    # === Menu Utils === #
    def _menu_button_clicked(self, index: int) -> None:
        """Handle sidebar menu button clicks.

        Args:
            index (int): The index of the clicked menu button.
        """
        self._change_main_view(index)

    def _change_main_view(self, index: int) -> None:
        """Change the main tab view based on the selected index.

        Args:
            index (int): The index of the new main tab.
        """
        self.main_tab_widget.setCurrentIndex(index)
        self._update_toolbar(index)

    def _toggle_sidebar(self) -> None:
        """Toggle the sidebar between collapsed and expanded states."""
        collapsed = self.sidebar.width() > 60
        if collapsed:
            self.sidebar.setFixedWidth(60)
            self.collapse_btn.set_collapsed(True)
            for btn in self.menu_buttons:
                btn.set_collapsed(True)
        else:
            self.sidebar.setFixedWidth(190)
            self.collapse_btn.set_collapsed(False)
            for btn in self.menu_buttons:
                btn.set_collapsed(False)

    '''def update_collapse_button(self):
        state = self.sidebar_states[self.current_sidebar_state]
        icon_path = resource_path(f"assets/icons/{state['icon']}")
        self.collapse_btn.setIcon(QIcon(str(icon_path)))
        self.collapse_btn.setToolTip(state["tooltip"])'''

    # === Triggers === #
    def change_triggered(self) -> None:
        """Handle changes in the database selection."""
        self.top_bar.get_current_database()

        scan_results: dict = self.web_browser_view.get_scan_results()

        # pause for half a second to ensure the UI is ready
        time.sleep(0.5)

        self.update_browser_settings(scan_results,
                                     self.web_browser_view.get_scan_behavior(
                                     ), self.top_bar.get_current_db_ids())

        self._init_document_insights_view()

        self._init_enrichment_module_view()

        if self.documents_view:
            if self.documents_view.table_widget is not None:
                self.documents_view.table_widget.update_db_path(
                    self.top_bar.get_current_database())

        self._update_toolbar(0)

    def _update_settings_panel(self, index: int) -> None:
        """Update the settings panel based on the current tab index.

        Args:
            index (int): The index of the current tab.
        """
        for i, btn in enumerate(self.menu_buttons):
            btn.set_active(i == index)

    def open_gene_info(self, gene_entrez_id: str) -> None:
        """Open the gene information view for the specified Entrez ID.

        Args:
            gene_entrez_id (str): The Entrez ID of the gene.
        """
        self.web_browser_view.add_new_gene_info_tab(
            gene_id=gene_entrez_id, switch_to=True)
        # show web view
        self._change_main_view(0)

    def open_article_info(self, article_id: str, name: str) -> None:
        """Open the article information view for the specified article ID.

        Args:
            article_id (str): The ID of the article.
            name (str): The name of the article.
        """
        self.web_browser_view.add_new_article_info_tab(
            article_id=article_id, db_name=name, switch_to=True)
        # show web view
        self._change_main_view(0)

    def _update_toolbar(self, index: int) -> None:
        """Update the toolbar actions based on the current tab index.

        Args:
            index (int): The index of the current tab.
        """
        if index == 0:  # Web Browser
            self.top_bar.set_toolbar_actions(
                self.web_browser_view.toolbar_actions)
            self.top_bar.set_toolbar2_actions(
                self.web_browser_view.toolbar_actions2)
            self.top_bar.toggle_toolbar2(True)
        elif index == 1:  # Document Insights
            self.top_bar.set_toolbar_actions(
                self.documents_view.toolbar_actions)
            self.top_bar.set_toolbar2_actions(
                self.documents_view.toolbar_actions2)
            self.top_bar.toggle_toolbar2(True)
        elif index == 2:  # Enrichment
            self.top_bar.set_toolbar_actions(
                self.gene_lists_view.toolbar_actions)
            self.top_bar.set_toolbar2_actions(
                self.gene_lists_view.toolbar_actions2)
            self.top_bar.toggle_toolbar2(True)
        elif index == 3:  # Compare Results
            self.top_bar.set_toolbar_actions(
                self.comparison_settings_kit.toolbar_actions)
            self.top_bar.set_toolbar2_actions(
                self.comparison_settings_kit.toolbar_actions2)
            self.top_bar.toggle_toolbar2(True)
        elif index == 4:  # Settings
            self.top_bar.set_toolbar_actions([])
            self.top_bar.set_toolbar2_actions([])
            self.top_bar.toggle_toolbar2(False)

    def update_browser_settings(self, article_ids: list,
                                scan_behavior: str, saved_ids: list) -> None:
        """Update the browser settings view with new article IDs and scan behavior.

        Args:
            article_ids (list): The list of article IDs.
            scan_behavior (str): The scan behavior setting.
            saved_ids (list): The list of saved article IDs.
        """
        self.browser_settings_view.update_articles(
            article_ids, scan_behavior, saved_ids)

    def update_comparison_view(self) -> None:
        """Update the enrichment comparison view based on the selected TSV files."""
        comparison_inputs = self.comparison_settings_kit.get_comparison_inputs()
        valid_tsv_1, errors1 = validate_tsv_file(
            comparison_inputs.get("file1", ""))
        valid_tsv_2, errors2 = validate_tsv_file(
            comparison_inputs.get("file2", ""))

        label1 = Path(comparison_inputs["file1"]).stem
        label2 = Path(comparison_inputs["file2"]).stem

        comparison_inputs["label1"] = label1
        comparison_inputs["label2"] = label2

        library = comparison_inputs.get("library", "Unknown Gene Set Library")

        if valid_tsv_1 and valid_tsv_2:
            self.comparison_html = create_comparison_html(
                tsv_a_path=comparison_inputs.get("file1", ""),
                tsv_b_path=comparison_inputs.get("file2", ""),
                label_a=label1,
                label_b=label2,
                library=library
            )
            self.enrichment_comparison_view.setHtml(self.comparison_html)

        else:
            text = """<p>Please upload valid TSV files for comparison.</p>"""
            if errors1:
                text += f"""<p>Errors in File 1:</p>
                <ul>{"".join(f"<li>{error}</li>" for error in errors1)}</ul>"""
            if errors2:
                text += f"""<p>Errors in File 2:</p>
                <ul>{"".join(f"<li>{error}</li>" for error in errors2)}</ul>"""

            self.comparison_html = text
            self.enrichment_comparison_view.setHtml(text)

    def export_comparison_to_html(self) -> None:
        """Export the current comparison view to an HTML file."""
        html_content = self.comparison_html

        # ask user where to save
        save_path, _ = QFileDialog.getSaveFileName(
            None,
            "Save Comparison Results",
            os.path.expanduser("~"),
            "HTML Files (*.html);;All Files (*)"
        )
        if save_path:
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(html_content)

    def collapse_log_panel(self) -> None:
        """Collapse the log panel."""
        self.middle_splitter.setSizes([700, 0])

    def expand_log_panel(self) -> None:
        """Expand the log panel."""
        self.middle_splitter.setSizes([500, 200])

    ##### ============ ARTICLE RETRIEVAL ============ #####
    def add_ids_to_database(self, selected_ids: dict) -> None:
        """Add selected article IDs to the current database.

        Args:
            selected_ids (dict): A dictionary containing "pmids" and "pmcids"
        """
        pmids = selected_ids.get("pmids", []) or []
        pmcids = selected_ids.get("pmcids", []) or []

        if not pmids and not pmcids:
            QMessageBox.warning(
                self, "No IDs Selected",
                "Please select at least one ID to add to the database.")
            return

        task_id = self.process_manager.add_indeterminate_task(
            "Article Retrieval")
        self.add_log_line(
            f"Retrieval started ({task_id}) · PMIDs={len(pmids)} · PMCIDs={len(pmcids)}")

        try:
            worker = ArticleRetrievalWorker(
                main_app=self,
                process_manager=self.process_manager,
                task_name=task_id,
                selected_ids=selected_ids,
                db_path=self.top_bar.get_current_database(),
                email=self.api_email,
                api_key=self.api_key
            )
            self._workers_by_task[task_id] = worker

            worker.signals.progress.connect(
                self.process_manager.update_task_progress)

            worker.signals.ui_update.connect(
                lambda tid, _payload: self.change_triggered())

            worker.signals.error.connect(lambda tid, msg: (
                self.process_manager.set_task_status(
                    tid, TaskStatus.ERROR, error_msg=msg),
                self.add_log_line(
                    f"Retrieval error ({tid}): {msg}", mode="ERROR")
            ))

            worker.signals.finished.connect(lambda tid, _payload: (
                self.process_manager.set_task_status(tid, TaskStatus.DONE),
                self.add_log_line(f"Retrieval finished ({tid})"),
                QMessageBox.information(self, "IDs Added",
                                        f"Successfully added {len(pmids)} PMIDs and {len(pmcids)} PMCIDs to the database.")
            ))

            QThreadPool.globalInstance().start(worker)

        except Exception as e:
            self.add_log_line(f"Failed to start retrieval: {e}", mode="ERROR")
            self.process_manager.set_task_status(
                task_id, TaskStatus.ERROR, error_msg=str(e))

    ##### ============ ENRICHMENT ANALYSIS ============ #####

    def species_changed(self, species_list: list) -> None:
        """Handle species change event.

        Args:
            species_list (list): The list of selected species.
        """
        if isinstance(self.gene_lists_view, EnrichmentModuleView):
            self.gene_lists_view.on_species_changed(species_list)

    def start_enrichment(self, gene_set: str, gene_symbols: list,
                         stat_test: str, stat_correction: str) -> None:
        """Start the enrichment analysis process.

        Args:
            gene_set (str): The selected gene set library.
            gene_symbols (list): The list of gene symbols for analysis.
            stat_test (str): The statistical test to use.
            stat_correction (str): The statistical correction method to use."""
        sort_by = "Adjusted P-value"  # self.gene_lists_settings.get_sort_by()

        task_id = self.process_manager.add_indeterminate_task(
            "Enrichment Analysis")
        self.add_log_line(
            f"Enrichment started ({task_id}) set={gene_set} n_genes={len(gene_symbols)}")

        try:
            enrichment_analysis_process = EnrichmentAnalysis(
                self,
                gene_list=gene_symbols,
                gene_sets=gene_set,
                sort_by=sort_by,
                stat_test=stat_test,
                stat_correction=stat_correction
            )
            worker = EnrichmentWorker(self, self.process_manager, task_id,
                                      enrichment_analysis_process)

            # keep a reference for controls
            self._workers_by_task[task_id] = worker

            # wire signals
            worker.signals.progress.connect(
                self.process_manager.update_task_progress)

            worker.signals.ui_update.connect(self._update_ui_after_enrichment)

            worker.signals.error.connect(lambda tid, msg: (
                self.process_manager.set_task_status(
                    tid, TaskStatus.ERROR, error_msg=msg),
                self.add_log_line(
                    f"Enrichment error ({tid}): {msg}", mode="ERROR")
            ))

            worker.signals.finished.connect(lambda tid, df: (
                self.process_manager.set_task_status(tid, TaskStatus.DONE),
                self.add_log_line(
                    f"Enrichment finished ({tid}), rows={0 if df is None else len(df)}")

            ))

            QThreadPool.globalInstance().start(worker)

        except Exception as e:
            self.add_log_line(f"Failed to start enrichment: {e}", mode="ERROR")
            self.process_manager.set_task_status(
                task_id, TaskStatus.ERROR, error_msg=str(e))

    def _update_ui_after_enrichment(self, task_id: str,
                                    results_df: pd.DataFrame) -> None:
        """Update the UI with enrichment results after analysis.

        Args:
            task_id (str): The ID of the enrichment task.
            results_df (DataFrame): The DataFrame containing enrichment results.
        """
        if results_df is None:
            self.add_log_line(
                f"No enrichment results ({task_id})", mode="WARNING")
            self.process_manager.set_task_status(task_id, TaskStatus.DONE)
            return

        self.gene_lists_view.show_retrieved_pathway_results(
            results_df=results_df)
        self.gene_lists_view.show_results_tab()

    def _handle_enrichment_finished(self, task_name: str,
                                    results_df: pd.DataFrame) -> None:
        """Handles the completion of enrichment analysis and updates the UI.

        Args:
            task_name (str): The name of the enrichment task.
            results_df (DataFrame): The DataFrame containing enrichment results.
        """
        if results_df is None:
            self.add_log_line(
                "No results found during enrichment.", mode="WARNING")
            self.process_manager.stop_task(task_name)
            return

        self.add_log_line(
            f"Enrichment analysis {task_name} completed successfully.", mode="INFO")
        self.process_manager.stop_task(task_name)

    def _handle_enrichment_error(self, task_name: str,
                                 error_message: str) -> None:
        """Handles errors occurring in the enrichment process.

        Args:
            task_name (str): The name of the enrichment task.
            error_message (str): The error message.
        """
        self.add_log_line(
            f"Error during {task_name}: {error_message}", mode="ERROR")
        self.process_manager.stop_task(task_name)

    def add_log_line(self, text: str, mode: str = "INFO") -> None:
        """Add a log line to the logs panel.

        Args:
            text (str): The log message.
            mode (str): The log mode, e.g., "INFO", "ERROR", "WARNING".
        """
        self.logs_panel.add_log(text + "\n", mode)

    ##### ==========GENE SET LIBRARIES ====== #####

    def update_gmt_libraries(self, libraries: list) -> None:
        """Update the gene set libraries in the enrichment module view.

        Args:
            libraries (list): The list of available gene set libraries.
        """
        if isinstance(self.gene_lists_view, EnrichmentModuleView):
            self.gene_lists_view.update_libraries_list(libraries)

    ##### ============ TASK BOARD ============ #####
    def _cancel_task_clicked(self, task_id: str) -> None:
        """Handle cancel task event.

        Args:
            task_id (str): The ID of the task to cancel.
        """
        wk = self._workers_by_task.get(task_id)
        if wk and hasattr(wk, "stop"):
            wk.stop()
        self.process_manager.set_task_status(task_id, TaskStatus.CANCELED)
        self.add_log_line(f"Canceled {task_id}")

    def _pause_task_clicked(self, task_id: str) -> None:
        """Handle pause task event.

        Args:
            task_id (str): The ID of the task to pause.
        """
        wk = self._workers_by_task.get(task_id)
        if wk and hasattr(wk, "pause"):
            wk.pause()
        self.process_manager.set_task_status(task_id, TaskStatus.PAUSED)
        self.add_log_line(f"Paused {task_id}")

    def _resume_task_clicked(self, task_id: str) -> None:
        """Handle resume task event.

        Args:
            task_id (str): The ID of the task to resume.
        """
        wk = self._workers_by_task.get(task_id)
        if wk and hasattr(wk, "resume"):
            wk.resume()
        self.process_manager.set_task_status(task_id, TaskStatus.RUNNING)
        self.add_log_line(f"Resumed {task_id}")

    ##### ============ STYLESHEET ============ #####
    def apply_stylesheet(self) -> None:
        """Apply the custom stylesheet to the application."""
        stylesheet_path = resource_path("assets/style/stylesheet.qss")
        if not stylesheet_path.exists():
            print(f"ERROR: The file does NOT exist at {stylesheet_path}")
            return
        try:
            with open(stylesheet_path, "r", encoding="utf-8") as f:
                stylesheet = f.read()
            self.setStyleSheet(stylesheet)
            if self.styleSheet() == "":
                print("ERROR: Stylesheet was NOT applied! Check for syntax errors.")
        except Exception as e:
            print(f"ERROR: Could not open stylesheet: {e}")

    ##### ============ APPLICATION EXIT ============ #####
    def closeEvent(self, event) -> None:
        """Handle application exit and ensure proper cleanup of web engine resources."""
        confirmation = QMessageBox.question(
            self, "Exit Application",
            "Are you sure you want to close? All running processes will be stopped.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if confirmation != QMessageBox.Yes:
            event.ignore()
            return

        # 1) Delete ALL WebEngineViews
        for v in self.findChildren(QWebEngineView):
            v.deleteLater()

        # 2) Delete any standalone QWebEnginePage
        for p in self.findChildren(QWebEnginePage):
            p.deleteLater()

        # 3) Let deletions run so pages really die before the profile
        QCoreApplication.processEvents()

        # 4) Safely release the shared profile
        self.web.shutdown()

        event.accept()
