"""Provides the bubble and bar plot widget for enrichment results in the enrichment module"""

# --- Standard Library Imports ---
import os
from datetime import datetime

# --- Third Party Imports ---
import numpy as np
import pandas as pd
from PyQt5.QtCore import QUrl
from PyQt5.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QMessageBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

# --- Local Imports ---
from app.enrichment_module.enrichment_results.interactive_plot_creation import (
    generate_interactive_bar_chart_html,
    generate_interactive_bubble_chart_html,
)
from app.util_widgets.clickable_widget import IconTextButton
from app.util_widgets.svg_button import SvgHoverButton

# --- Public Classes ---


class BubbleBarPlotWidget(QWidget):
    """Widget containing bubble plot and bar plot tabs for enrichment results."""

    def __init__(self, dataframe: pd.DataFrame, main_app):
        """
        Initialize the BubbleBarPlotWidget.
        It contains tabs for bubble plot and bar plot visualizations of enrichment results.

        Args:
            dataframe: DataFrame containing enrichment results.
            main_app: The main application instance.
        """
        super().__init__()

        self.main_app = main_app

        # Store the original DataFrame
        self.raw_data: pd.DataFrame = dataframe.copy()
        self.data: pd.DataFrame = self._preprocess_data(self.raw_data)

        # Main Layout with Tabs
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.tabs = QTabWidget()

        self.bubble_plot_html_path: str = None
        self.bar_plot_html_path: str = None

        # Create WebEngineViews for each tab
        self.bubble_tab = self.main_app.get_new_web_view()
        self.bar_tab = self.main_app.get_new_web_view()

        # Add tabs
        self.tabs.addTab(self.bubble_tab, "Bubble Plot")
        self.tabs.addTab(self.bar_tab, "Bar Plot")

        # hide tab bar
        self.tabs.tabBar().hide()

        # hboxlayout and widget containing the buttons
        self.button_widget = QWidget()
        self.button_layout = QHBoxLayout(self.button_widget)

        self.button_layout.setContentsMargins(0, 0, 0, 0)
        self.button_layout.setSpacing(5)

        self.button_widget.setFixedHeight(30)

        term_toolbar = QWidget()
        term_toolbar_layout = QHBoxLayout(term_toolbar)
        term_toolbar_layout.setContentsMargins(0, 0, 0, 0)
        term_toolbar_layout.setSpacing(5)
        term_toolbar_layout.addStretch()

        self.main_layout.addWidget(term_toolbar)

        self._show_bubble_plot_btn = IconTextButton(
            "Bubble Plot",          # label
            "bubble_plot3",       # icon key/name
            "Show Bubble Plot",          # tooltip
            24,                  # icon size
            fct=lambda: self._show_bubble_plot()
        )

        self.show_bar_plot_btn = IconTextButton(
            "Bar Plot",          # label
            "bar_plot3",       # icon key/name
            "Show Bar Plot",          # tooltip
            24,                  # icon size
            fct=lambda: self._show_bar_plot()
        )

        self._show_bubble_plot_btn.setFixedWidth(130)
        self.show_bar_plot_btn.setFixedWidth(110)

        self._export_plot_btn = SvgHoverButton(
            base_name="export",
            tooltip="Export Plots",
            triggered_func=lambda: self._export_plot(),
            size=20,
            parent=self
        )

        term_toolbar_layout.addWidget(self._show_bubble_plot_btn)
        term_toolbar_layout.addWidget(self.show_bar_plot_btn)

        term_toolbar_layout.addStretch(1)
        term_toolbar_layout.addWidget(self._export_plot_btn)

        # Add tabs to layout
        self.main_layout.addWidget(self.tabs)

        # Initialize plots
        self._update_bubble_plot()
        self._update_bar_plot()

    # --- Private Methods ---
    def _show_bubble_plot(self) -> None:
        """Set current tab to bubble tab."""
        self.tabs.setCurrentWidget(self.bubble_tab)

    def _show_bar_plot(self) -> None:
        """Set current tab to bar tab."""
        self.tabs.setCurrentWidget(self.bar_tab)

    def _preprocess_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Process the input DataFrame to extract useful numerical values.

        Args:
            df: DataFrame containing enrichment results.

        Returns:
            pd.DataFrame: Processed DataFrame with additional numerical columns.
        """
        df = df.copy()

        # Extract Overlap Count and Term Size from the "Overlap" column
        df[["Overlap Count", "Term Size (from Overlap)"]] = df["Overlap"].str.extract(
            r"(\d+)/(\d+)").astype(float)

        # Use Term Size from the actual "Term Size" column if it exists
        if "Term Size" in df.columns:
            df["Total Genes"] = df["Term Size"]
        else:
            df["Total Genes"] = df["Term Size (from Overlap)"]

        # Compute Overlap Ratio
        df["Overlap Ratio"] = df["Overlap Count"] / df["Total Genes"]

        # Convert numeric columns
        numeric_cols = ["P-value", "Adjusted P-value",
                        "Odds Ratio", "Combined Score"]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        # Log-transform P-values
        df["-log10 P-value"] = -np.log10(df["P-value"])
        df["-log10 Adjusted P-value"] = -np.log10(df["Adjusted P-value"])

        # If needed, assign "Gene Count" to Overlap Count
        df["Gene Count"] = df["Overlap Count"]

        return df

    def _update_bar_plot(self) -> None:
        """Generate and display the bar plot with a simple timestamp (day-month_hour-minute)."""
        # Create a human-readable timestamp: day-month_hour-minute
        timestamp = datetime.now().strftime("%d-%m_%H-%M")

        # Build the output file path in an OS-independent way
        filename = f"bar_chart_{timestamp}.html"
        output_file = os.path.join(self.main_app.folder_path, filename)

        # Generate the interactive bar chart HTML
        generate_interactive_bar_chart_html(
            df=self.data,
            output_file=output_file
        )

        # Load the bar chart in the correct tab
        self.bar_tab.load(QUrl.fromLocalFile(output_file))
        self.bar_tab.setZoomFactor(0.8)
        self.bar_tab.show()

        # Store the final HTML path
        self.bar_plot_html_path = output_file

    def _update_bubble_plot(self) -> None:
        """Generate and display the bubble plot."""
        # Create a human-readable timestamp: day-month_hour-minute
        timestamp = datetime.now().strftime("%d-%m_%H-%M")

        # Build the output file path in an OS-independent way
        filename = f"bubble_chart_{timestamp}.html"
        output_file = os.path.join(self.main_app.folder_path, filename)

        generate_interactive_bubble_chart_html(
            df=self.data,
            output_file=output_file
        )

        # Load the bubble chart in the correct tab
        self.bubble_tab.load(QUrl.fromLocalFile(output_file))

        self.bubble_tab.setZoomFactor(0.8)
        self.bubble_tab.show()

        self.bubble_plot_html_path = output_file

    def _export_plot(self) -> None:
        """Export the current plot (bubble or bar) to an HTML file."""
        # check which tab is currently active
        current_tab = self.tabs.currentIndex()

        html_path = None
        if current_tab == 0:
            html_path = self.bubble_plot_html_path
        elif current_tab == 1:
            html_path = self.bubble_plot_html_path

        # check if the comparison results are available
        if html_path is None:
            QMessageBox.critical(
                self, "Error", "Please perform pathway enrichment first.")
            return

        html_content = open(html_path, encoding='utf-8').read()
        # ask the user if they want to export the results
        message = "Do you want to export the interactive comparison? (Saves a *.html file)"
        export = QMessageBox.question(
            self, "Export Results", message, QMessageBox.Yes | QMessageBox.No)

        if export == QMessageBox.Yes:
            # get the file name and location to save the file
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save File", "", "HTML Files (*.html);")
            if file_path:
                if not file_path.endswith(".html"):
                    file_path += ".html"
                if file_path.endswith(".html"):
                    # save the results as an html file
                    with open(file_path, "w", encoding='utf-8') as file:
                        file.write(html_content)
        else:
            return
