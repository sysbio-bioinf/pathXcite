"""View for documents, gene lists, stats, pathways, and plots in the enrichment module"""

# --- Standard Library Imports ---
import json
import os
from dataclasses import dataclass
from typing import List, Tuple

# --- Third Party Imports ---
import pandas as pd
from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)

# --- Local Imports ---
from app.database.database_query import retrieve_document_data
from app.enrichment_module.document_selection.documents_tab_widget import (
    DocumentsTabWidget,
)
from app.enrichment_module.enrichment_results.bubble_bar_plot_widget import (
    BubbleBarPlotWidget,
)
from app.enrichment_module.enrichment_results.enrichment_results_widget import (
    EnrichmentResultsWidget,
)
from app.enrichment_module.gene_selection.gene_tab_widget import GeneTabWidget
from app.enrichment_module.gene_selection.gfidf_computation import compute_gfidf
from app.util_widgets.clickable_widget import IconTextButton
from app.util_widgets.multi_dropdown import MultiSelectDropdownToolButton
from app.util_widgets.single_dropdown import SingleSelectDropdownToolButton
from app.util_widgets.svg_button import SvgButton, SvgHoverButton
from app.utils import get_default_html_svg, resource_path

# --- Public Classes ---


@dataclass(frozen=True)
class TabItem:
    """Data class representing a tab item with title and icon key."""
    title: str
    icon_key: str


class EnrichmentModuleView(QWidget):
    """View for documents, gene lists, stats, pathways, and plots.
    Tabs are hidden; a custom button bar controls which tab is shown.
    """

    def __init__(self, main_app):
        """ Initializes the enrichment module view with tabs and custom controls.

        Args:
            main_app: Reference to the main application.
        """
        super().__init__()

        self.main_app = main_app

        self._tab_height = 34
        self._group_spacing = 0
        self._btn_layout_spacing = 2
        self._bar_spacing = 6
        self._bar_margins = (0, 0, 0, 0)
        self._btn_margins = (2, 2, 2, 2)
        self._group_stylesheet = """
            QWidget {
                background-color: transparent;
                border: 0px solid gray;
            }
        """

        # ------------------------------- State (unchanged) -------------------------------
        self.folder_path: str = self.main_app.folder_path

        self.db_path: str = self.main_app.get_current_database()

        self.db_path: str = None
        self.plot_creator = None
        self.show_documents_without_genes = True  # Default: Show all documents
        self.toolbar_actions: list[QWidgetAction] = []
        self.toolbar_actions2: list[QWidgetAction] = []
        self.current_doc_set_stats: dict = None
        self.current_gene_data: list[list]
        self.gene_gfidf_map: dict[str, float]
        self.pathway_gene_set: str
        self.plot_creator_tab: QWidget
        # self.enrichmentResultsTable: QWidget

        self.results_df: pd.DataFrame = None
        self.selected_species: list[str] = []

        self.checked_pubmed_ids = set()

        # ------------------------------- Root layout/splitter ----------------------------
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # Splitter divides left (Documents tree) and right (buttons + tab content)
        self.splitter = QSplitter()
        main_layout.addWidget(self.splitter)

        # ------------------------------- RIGHT: Controls + Tab content -------------------
        # Right container holds the custom button bar + the (hidden) QTabWidget
        self.right_panel = QWidget()
        self.right_layout = QVBoxLayout(self.right_panel)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.right_layout.setSpacing(8)

        # QTabWidget keeps all the existing tab content
        self.tab_widget = QTabWidget()

        # ---- Add all tabs ----
        # 1) Documents
        # ------------------------------- LEFT: Documents panel ---------------------------
        self._build_documents_panel()

        # 3) Gene list (stack with warning)
        self._build_gene_list_tab()

        # 4) Gene info tab
        self.gene_info_tab = QWidget()
        self.init_gene_info_tab()

        self._build_ora_results_tab()
        # 6) Plots tab
        self._build_plots_tab()

        # ---- Hide the native tab bar (only content remains) ----
        self.tab_widget.tabBar().hide()

        # ---- Build the external button bar to control the shown tab ----
        self._build_tab_controls()
        # Add the (hidden-bar) tab widget beneath the buttons
        self.right_layout.addWidget(self.tab_widget)
        # Put RIGHT side into the splitter
        self.splitter.addWidget(self.right_panel)
        # ------------------------------- Other initializations (unchanged) ---------------
        self.init_toolbar_actions()
        self.documents_splitter.update_document_list()

    # ==============================================================================
    # UI builders
    # ==============================================================================

    def _build_documents_panel(self) -> QWidget:
        """Creates the original Documents panel (tree + checkbox)."""
        self.documents_splitter = DocumentsTabWidget(
            self.main_app, self)  # QSplitter()
        self.tab_widget.addTab(self.documents_splitter, "Documents")

    def _build_gene_list_tab(self) -> None:
        """Gene List as a stacked page with a default 'no genes' webview."""
        self.genes_tab_stackwidget = GeneTabWidget(self.main_app, self)
        self.tab_widget.addTab(self.genes_tab_stackwidget, "Gene List")

        self.genes_tab_stackwidget.init_gene_list_tab()
        self.genes_tab = self.genes_tab_stackwidget.get_genes_tab()
        self.no_genes_warning = self.genes_tab_stackwidget.get_no_genes_warning()
        self.gene_selection_left_widget = self.genes_tab_stackwidget.get_gene_selection_left_widget()
        self.menu_bar = self.genes_tab_stackwidget.get_menu_bar()
        self.filter_line_edit = self.genes_tab_stackwidget.get_filter_line_edit()
        self.filter_combo = self.genes_tab_stackwidget.get_filter_combo()
        self.gene_list_table = self.genes_tab_stackwidget.get_gene_list_table()
        self.export_gene_btn = self.genes_tab_stackwidget.get_export_gene_btn()
        self.select_all_genes_checkbox = self.genes_tab_stackwidget.get_select_all_genes_checkbox()

    def _build_ora_results_tab(self) -> None:
        """Gene List as a stacked page with a default 'no genes' webview."""
        self.results_tab = EnrichmentResultsWidget(self.main_app, None)
        self.tab_widget.addTab(self.results_tab, "View Results")

    def _build_plots_tab(self) -> None:
        """Plots tab (web view)."""
        self.plot_creator_tab = self.main_app.get_new_web_view(parent=self)
        message = "Please start enrichment process to get insights into enriched terms."
        self.plot_creator_tab.setHtml(
            get_default_html_svg(str(resource_path("assets/icons/stats.svg")),
                                 message)
        )
        self.tab_widget.addTab(self.plot_creator_tab, "Plots")

    def _on_tab_button_clicked(self, index: int) -> None:
        """Switch to tab at index and update icon states.

        Args:
            index: Index of the tab to switch to.
        """
        self.tab_widget.setCurrentIndex(index)
        self._update_tab_button_states(index)

    def _update_tab_button_states(self, active_index: int) -> None:
        """Reflect which icon is active.

        Args:
            active_index: Index of the currently active tab.
        """
        if not hasattr(self, "_tab_buttons"):
            return
        for i, btn in enumerate(self._tab_buttons):
            is_active = i == active_index

            if hasattr(btn, "setChecked"):
                try:
                    btn.setChecked(is_active)
                except Exception:
                    pass
            if hasattr(btn, "setActive"):
                try:
                    btn.setActive(is_active)
                except Exception:
                    pass
            if hasattr(btn, "setSelected"):
                try:
                    btn.setSelected(is_active)
                except Exception:
                    pass

            # fallback
            try:
                btn.setProperty("active", is_active)
                btn.style().unpolish(btn)
                btn.style().polish(btn)
                btn.update()
            except Exception:
                pass

    def _build_tab_controls(self) -> None:
        """Create a custom bar of IconTextButton items to control which tab is shown."""
        self.tab_controls_bar = QWidget()
        bar_layout = QHBoxLayout(self.tab_controls_bar)
        bar_layout.setContentsMargins(*self._bar_margins)
        bar_layout.setSpacing(self._bar_spacing)

        # Keep a flat list of buttons in tab order
        self._tab_buttons: List[IconTextButton] = []

        # Define groups in the order they appear
        groups: List[Tuple[int, List[TabItem]]] = [
            (1, [
                TabItem("Select Documents",  "doc_selection")  # ,
                # TabItem("View Statistics", "doc_stats"),
            ]),
            (2, [
                TabItem("Select Genes",  "gene_selection"),
            ]),
            (3, [
                TabItem("View Results", "pea_result"),
                TabItem("View Plots",      "pea_plots")
            ]),
        ]

        next_tab_index = 0  # running index across all tabs

        for step_number, items in groups:
            group_widget, created_buttons = self._create_tab_group(
                step_number, items, start_index=next_tab_index)
            self._tab_buttons.extend(created_buttons)
            next_tab_index += len(created_buttons)

            bar_layout.addWidget(group_widget)
            # add spacing between groups (except after the last one)
            if (step_number, items) != groups[-1]:
                bar_layout.addSpacing(self._group_spacing)

        bar_layout.addStretch()

        # place the bar above the content
        self.right_layout.addWidget(self.tab_controls_bar)

        # make the current tabs icon look active
        self._update_tab_button_states(self.tab_widget.currentIndex())

    # ---------- helpers ----------

    def _create_tab_group(self, step_number: int, items: List[TabItem],
                          start_index: int) -> Tuple[QWidget, List['IconTextButton']]:
        """Builds a horizontal group with a leading step label and one or more tab buttons.

        Args:
            step_number: Step number to display on the left.
            items: List of TabItem for each button in the group.
            start_index: Starting index for the tab buttons.

        Returns:
                A tuple containing the group widget and a list of created tab buttons.
        """
        group = QWidget()
        layout = QHBoxLayout(group)
        layout.setContentsMargins(*self._btn_margins)
        layout.setSpacing(self._btn_layout_spacing)
        group.setFixedHeight(self._tab_height)
        group.setStyleSheet(self._group_stylesheet)

        right_arrow = SvgButton(
            "right_arrow.svg", tooltip="Next", triggered_func=None, size=24)
        layout.addWidget(right_arrow)

        buttons: List[IconTextButton] = []
        for offset, item in enumerate(items):
            tab_index = start_index + offset
            btn = self._create_icon_button(item, tab_index, step_number)
            layout.addWidget(btn)
            buttons.append(btn)

        return group, buttons

    def _create_icon_button(self, item: TabItem, tab_index: int,
                            step_number: int) -> 'IconTextButton':
        """Factory for IconTextButton with consistent sizing and callback behavior.

        Args:
            item: TabItem defining the button.
            tab_index: Index of the tab this button controls.
            step_number: Step number for sizing logic.

        Returns:
            Configured IconTextButton instance.
        """
        btn = IconTextButton(
            item.title,  # label
            item.icon_key,  # icon key/name
            item.title,  # tooltip
            24,  # icon size
            fct=lambda *_, i=tab_index: self._on_tab_button_clicked(i),
        )
        if step_number == 1:
            if item.title == "Select Documents":
                btn.setFixedWidth(170)
            elif item.title == "View Statistics":
                btn.setFixedWidth(150)

        elif step_number == 2:
            btn.setFixedWidth(140)
        elif step_number == 3:
            if item.title == "View Plots":
                btn.setFixedWidth(125)
            elif item.title == "View Results":
                btn.setFixedWidth(140)
        return btn

    ### TOOLBAR ###
    def init_toolbar_actions(self) -> None:
        """ Initializes toolbar actions for species and gene set library selection. """
        # self.gene_set_libraries_dropdown = QComboBox()
        gene_set_libraries: List[str] = []
        # check if folder at assets/external_data/gmt_files exists
        if os.path.exists(resource_path("assets/external_data/gmt_files")):
            # add each file name to the dropdown
            for file_name in os.listdir(resource_path("assets/external_data/gmt_files")):
                if file_name.endswith(".gmt"):
                    gene_set_libraries.append(file_name.replace(".gmt", ""))

        if os.path.exists(resource_path("assets/external_data/custom_gmt_files")):
            # add each file name to the dropdown
            for file_name in os.listdir(resource_path("assets/external_data/custom_gmt_files")):
                custom_file_name = file_name.replace(".gmt", "")
                if custom_file_name not in gene_set_libraries and file_name.endswith(".gmt"):
                    gene_set_libraries.append(custom_file_name)

        gene_set_libraries = sorted(gene_set_libraries)

        self.start_enrichment_button = IconTextButton("Start Enrichment", "star2",
                                                      "Click to start enrichment", 20,
                                                      lambda: self.update_pea_results())
        self.start_enrichment_button.setFixedWidth(155)

        with open(resource_path("assets/external_data/gene2organism_mapping/tax2name.json"),
                  encoding="utf-8") as f:
            self.tax2name = json.load(f)

        items = [f"{name} ({tax_id})" for tax_id,
                 name in self.tax2name.items()]

        # Wrap each widget in a QWidgetAction so TopBar can render them
        def wrap(widget):
            act = QWidgetAction(self)  # parent = page (WebBrowser)
            # toolbar will merely show it, not own it
            act.setDefaultWidget(widget)
            return act

        self.species_selector_widget = SvgHoverButton(
            "taxFilter", tooltip=None, triggered_func=None, width=51, height=30)

        self.species_selection_dropdown = MultiSelectDropdownToolButton(
            base_text="Select species...",
            items=items,
            parent=None,
            main_app=self.main_app,
            button=self.species_selector_widget,
            collapsed_visual=lambda b: b.setBaseName("taxFilter"),
            expanded_visual=lambda b: b.setBaseName("taxFilter2"),
            on_selection_change=None
        )

        self.species_selection_dropdown.selectionChanged.connect(
            self.on_species_selection_signal)

        self.gene_set_library_selector_widget = SvgHoverButton(
            "library", tooltip=None, triggered_func=None, width=51, height=30)

        self.gene_set_library_selector = SingleSelectDropdownToolButton(base_text="Select gene set library...",
                                                                        items=sorted(
                                                                            gene_set_libraries),
                                                                        parent=None,
                                                                        button=self.gene_set_library_selector_widget,
                                                                        collapsed_visual=lambda b: getattr(
                                                                            b, "setBaseName")("library"),
                                                                        expanded_visual=lambda b: getattr(
                                                                            b, "setBaseName")("library2")
                                                                        )

        test_methods = [
            "Fisher's exact test",
            "Hypergeometric test"
        ]

        self.stat_test_selector_btn = SvgHoverButton(
            "statTest", tooltip=None, triggered_func=None, width=51, height=30)
        self.stat_test_selection_dropdown = SingleSelectDropdownToolButton(base_text="Select Statistical Test Method...",
                                                                           items=test_methods, parent=None,
                                                                           button=self.stat_test_selector_btn,
                                                                           item_name="Statistical Test Method",
                                                                           collapsed_visual=lambda b: getattr(
                                                                               b, "setBaseName")("statTest"),
                                                                           expanded_visual=lambda b: getattr(
                                                                               b, "setBaseName")("statTest2"),
                                                                           )

        correction_methods = [
            "Benjamini-Hochberg procedure (FDR)",
            "Benjamini-Yekutieli procedure (FDR)",
            "Bonferroni correction",
            "Sidak correction",
            "Holm-Sidak method",
            "Holm's method",
            "Simes-Hochberg procedure",
            "Hommel's method",
            "Two-stage Benjamini-Hochberg",
            "Two-stage Benjamini-Krieger-Yekutieli"
        ]

        self.stat_correction_selector_widget = SvgHoverButton("statCorrection",
                                                              tooltip=None, triggered_func=None, width=51, height=30)
        self.stat_correction_selection_dropdown = SingleSelectDropdownToolButton(base_text="Select Statistical Correction Method...",
                                                                                 items=correction_methods, parent=None,
                                                                                 button=self.stat_correction_selector_widget,
                                                                                 collapsed_visual=lambda b: getattr(
                                                                                     b, "setBaseName")("statCorrection"),
                                                                                 expanded_visual=lambda b: getattr(
                                                                                     b, "setBaseName")("statCorrection2"),
                                                                                 item_name="Correction"
                                                                                 )

        self.stat_test_selection_dropdown.set_selected_item(
            "Fisher's exact test")
        self.stat_correction_selection_dropdown.set_selected_item(
            "Benjamini-Hochberg procedure (FDR)")

        self.species_selection_dropdown.setFixedWidth(250)
        # self.gene_set_library_selector.setFixedWidth(260)
        self.stat_test_selection_dropdown.setFixedWidth(5)
        self.stat_correction_selection_dropdown.setFixedWidth(300)

        self.toolbar_actions.extend([
            wrap(self.species_selection_dropdown),
            wrap(self.gene_set_library_selector)

        ])

        self.toolbar_actions2.extend([
            wrap(self.stat_correction_selection_dropdown),
            wrap(self.start_enrichment_button)
        ])

    def on_species_selection_signal(self, checked_items: list[str]) -> None:
        """ Slot for species selection changes.

        Args:
            checked_items (list[str]): The list of checked species items.
        """
        species_list = checked_items or self.species_selection_dropdown.get_all_items()
        self.selected_species = species_list
        self.update_gene_list_tab()

    ### TAB INITIALIZATION ###

    def init_gene_info_tab(self) -> None:
        """ Initializes the Gene Info tab with a web view to NCBI Gene info page. """
        self.gene_web_view = self.main_app.get_new_web_view(parent=self)
        # open ncbi gene info page
        self.gene_web_view.setUrl(QUrl("https://www.ncbi.nlm.nih.gov/gene/"))
        info_layout = QVBoxLayout()
        info_layout.addWidget(self.gene_web_view)
        self.gene_info_tab.setLayout(info_layout)

    ### UPDATE VIEWS ###
    def on_species_changed(self, selected_species: list[str] = None) -> None:
        """Handles changes in selected species and updates gene list tab.

        Args:
            selected_species: List of selected species (Tax IDs). If None, uses current selection.
        """
        self.selected_species: list[str] = self.species_selection_dropdown.get_selected_items(
            include_unchecked=True)
        self.update_gene_list_tab()

    def show_results_tab(self) -> None:
        """Switches to the Results tab."""
        self.tab_widget.setCurrentIndex(2)
        self._update_tab_button_states(2)

    def update_gene_list_tab(self) -> None:
        """Updates the gene list tab based on selected documents and species."""
        self.documents_splitter.update_stats_tab()

        # checked_pubmed_ids = self.documents_splitter.get_checked_pubmed_ids()

        self.current_gene_data: list[list] = []  # Clear previous data
        # Dictionary to store aggregated gene data
        gene_accumulator: dict[str, dict] = {}

        self.selected_species = self.species_selection_dropdown.get_selected_items(
            include_unchecked=True)
        print("Selected species for gene list update:", self.selected_species)

        taxids = [str(species.split(" ")[-1].replace("(", "").replace(")", ""))
                  for species in self.selected_species]
        for pubmed_id in self.documents_splitter.get_checked_pubmed_ids():
            document_data = retrieve_document_data(pubmed_id, self.db_path)
            num_genes = len(document_data.get("annotations", {}))
            self.documents_splitter.retrieved_document_data_dict[pubmed_id] = {
                'document_data': document_data, 'num_genes': num_genes}

            # Skip documents without genes if filtering is enabled
            if num_genes == 0 and not self.show_documents_without_genes:
                continue

            annotations = document_data.get("annotations", {})
            for (entrez_id, gene_symbol, tax_id), annotation_list in annotations.items():
                # Filter by selected species
                if self.selected_species and str(tax_id[0]) not in taxids:
                    print(
                        f"Skipping gene {gene_symbol} (Entrez ID: {entrez_id}) due to species filter. Tax ID: {tax_id}")
                    continue
                num_annotations = len(annotation_list)

                # Aggregate num_annotations if gene already exists in dictionary
                if entrez_id in gene_accumulator:
                    gene_accumulator[entrez_id]["num_annotations"] += num_annotations
                    gene_accumulator[entrez_id]["annotation_list"].extend(
                        annotation_list)
                else:
                    gene_accumulator[entrez_id] = {
                        "gene_symbol": gene_symbol,
                        "num_annotations": num_annotations,
                        "tax_id": tax_id,
                        "annotation_list": annotation_list
                    }

        # Convert aggregated data into the final list format
        self.current_gene_data = [
            [entrez_id, data["gene_symbol"], data["num_annotations"],
                data["tax_id"], data["annotation_list"]]
            for entrez_id, data in gene_accumulator.items()
        ]
        # Compute GFIDF for each unique gene
        self.gene_gfidf_map = compute_gfidf(self.current_gene_data)

        # Add GFIDF score to gene data
        self.current_gene_data = [
            [entrez_id, data["gene_symbol"], data["num_annotations"], data["tax_id"],
                self.gene_gfidf_map.get(entrez_id, 0), data["annotation_list"]]
            for entrez_id, data in gene_accumulator.items()
        ]

        # if no entries are in current gene data, hide table
        if not self.current_gene_data:
            self.genes_tab_stackwidget.show_warning()
        else:
            self.genes_tab_stackwidget.show_table()

        self.genes_tab_stackwidget.update()

    def get_marked_rows(self) -> list[list[str]]:
        """ 
        Retrieves the contents of marked rows in the gene list table.
            If no rows are marked, returns all rows.
        Returns:
            A list of lists, where each inner list represents a row's contents.
        """
        row_contents: list[list[str]] = []
        header = [self.gene_list_table.horizontalHeaderItem(
            i).text() for i in range(self.gene_list_table.columnCount())]
        row_contents.append(header)

        # then add the marked rows (not the checked ones, but the marked ones)
        for row in range(self.gene_list_table.rowCount()):
            if self.gene_list_table.item(row, 0).background() == QColor(255, 255, 0):
                row_content = [self.gene_list_table.item(row, col).text(
                ) for col in range(self.gene_list_table.columnCount())]
                row_contents.append(row_content)

        if len(row_contents) > 1:
            return row_contents
        else:
            # return all
            for row in range(self.gene_list_table.rowCount()):
                row_content = [self.gene_list_table.item(row, col).text(
                ) for col in range(self.gene_list_table.columnCount())]
                row_contents.append(row_content)
            return row_contents

    def update_libraries_list(self, new_libraries) -> None:
        """ Updates the gene set libraries dropdown with new libraries."""
        # if new_libraries:
        #    self.gene_set_library_selector.setOptions(new_libraries)

        gene_set_libraries = []
        # check if folder at assets/external_data/gmt_files exists
        if os.path.exists(resource_path("assets/external_data/gmt_files")):
            # add each file name to the dropdown
            for file_name in os.listdir(resource_path("assets/external_data/gmt_files")):
                if file_name.endswith(".gmt"):
                    gene_set_libraries.append(file_name.replace(".gmt", ""))

        if os.path.exists(resource_path("assets/external_data/custom_gmt_files")):
            # add each file name to the dropdown
            for file_name in os.listdir(resource_path("assets/external_data/custom_gmt_files")):
                custom_file_name = file_name.replace(".gmt", "")
                if custom_file_name not in gene_set_libraries and file_name.endswith(".gmt"):
                    gene_set_libraries.append(custom_file_name)

        gene_set_libraries = sorted(list(set(gene_set_libraries)))
        if gene_set_libraries:
            self.gene_set_library_selector.set_options(gene_set_libraries)

    ### ---------- OVERREPRESENTATION ANALYSIS ----------- ###
    # RUN

    def update_pathway_result_tab(self, new_dataframe: pd.DataFrame) -> None:
        """ Updates the pathway enrichment analysis results tab with new data."""
        self.results_tab.set_dataframe(new_dataframe)

    def update_pea_results(self) -> None:
        """ Initiates the pathway enrichment analysis process. """
        self.plot_creator_tab = self.main_app.get_new_web_view(parent=self)

        self.results_tab.update_html("Enrichment process running...")
        icon_path = resource_path("assets/icons/stats.svg")
        self.plot_creator_tab.setHtml(get_default_html_svg(str(icon_path),
                                                           "Enrichment process running..."))

        # Updates the pathway enrichment analysis results.
        gene_symbols = [g.get('gene_symbol')
                        for g in self.genes_tab_stackwidget.selected_genes]

        self.pathway_gene_set = self.gene_set_library_selector.get_selected_item()

        if self.pathway_gene_set and gene_symbols:
            try:
                # self.enrichmentResultsTable.deleteLater()
                self.results_df = None
            except Exception:
                pass

            self.main_app.start_enrichment(self.pathway_gene_set, gene_symbols,
                                           self.stat_test_selection_dropdown.get_selected_item(),
                                           # organism, gene_symbols)
                                           self.stat_correction_selection_dropdown.get_selected_item())

        else:
            print("No pathway gene set selected or no genes selected.")
            if not self.pathway_gene_set:
                print("No pathway gene set selected.")
            if not gene_symbols:
                print("No genes selected.")

    # RESULTS
    # , enrichmentPlotWidget=None):
    def show_retrieved_pathway_results(self, results_df):
        """ Displays the retrieved pathway enrichment results. """
        # self.enrichmentResultsTable = enrichment_results_table
        self.results_df = results_df

        if self.results_df is None:
            print("No results found (None).")
            self.update_pathway_result_tab(self.results_df)

        else:
            if not self.results_df.empty:
                self.plot_creator = BubbleBarPlotWidget(
                    self.results_df, self.main_app)
                self.update_pathway_result_tab(self.results_df)
                self.update_plot_creator_tab(self.plot_creator)
            else:
                print("No results found (empty).")

    # SAVE
    def update_plot_creator_tab(self, new_content) -> None:
        """ Updates the Plot Creator tab with new content. """
        # Create a new widget for the updated Pathways tab
        new_plot_creator_tab = QWidget()
        new_layout = QVBoxLayout(new_plot_creator_tab)

        # Add new content
        new_layout.addWidget(new_content)

        # Replace the existing tab (assuming it is at index 3, i.e., the 4th tab)
        self.tab_widget.removeTab(3)
        self.tab_widget.insertTab(3, new_plot_creator_tab, "Plots")

        # Update the reference to the new tab
        self.plot_creator_tab = new_plot_creator_tab
