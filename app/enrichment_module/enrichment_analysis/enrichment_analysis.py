"""Provides the enrichment analysis functionality for the enrichment module"""

# --- Standard Library Imports ---
import time

# -- Third Party Imports ---
import pandas as pd

# --- Local Imports ---
from app.enrichment_module.enrichment_analysis.ora_computation import ora

# --- Public Classes ---


class EnrichmentAnalysis:
    """Provides the enrichment analysis functionality for the enrichment module."""

    def __init__(self, main_app, gene_list, gene_sets="KEGG_2021_Human",
                 organism="human", cutoff=0.05, sort_by="Adjusted P-value",
                 stat_test="Fisher's exact test",
                 stat_correction="Benjamini-Hochberg procedure (FDR)"):
        """Initialize the EnrichmentAnalysis instance.

        It sets up parameters for performing pathway enrichment analysis using ORA.
        Args:
            main_app: The main application instance.
            gene_list: List of genes for enrichment analysis.
            gene_sets: The gene set library to use (default: "KEGG_2021_Human").
            organism: The organism for the analysis (default: "human").
            cutoff: Significance cutoff for adjusted p-values (default: 0.05).
            sort_by: Column name to sort results by (default: "Adjusted P-value").
            stat_test: Statistical test to use (default: "Fisher's exact test").
            stat_correction: Multiple testing correction method (default:
               "Benjamini-Hochberg procedure (FDR)").
        """
        self.main_app = main_app
        self.gene_list = gene_list
        self.gene_sets = gene_sets
        self.organism = organism
        self.cutoff = 1
        self.sort_by = sort_by
        self.results_df = None
        self.max_retries = 3
        self.retry_delay = 2
        self.enr = None
        self.is_running = True
        self.is_paused = False

        test_method_to_param = {
            "Fisher's exact test": 'fisher',
            "Hypergeometric test": 'hypergeom',
            "Chi-squared test": 'chi2',
            "Binomial test": 'binomial',
            "Z-test for proportions": 'ztest'
        }

        correction_method_to_param = {
            "Bonferroni correction": 'bonferroni',
            "Sidak correction": 'sidak',
            "Holm-Sidak method": 'holm-sidak',
            "Holm's method": 'holm',
            "Simes-Hochberg procedure": 'simes-hochberg',
            "Hommel's method": 'hommel',
            "Benjamini-Hochberg procedure (FDR)": 'fdr_bh',
            "Benjamini-Yekutieli procedure (FDR)": 'fdr_by',
            "Two-stage Benjamini-Hochberg": 'fdr_tsbh',
            "Two-stage Benjamini-Krieger-Yekutieli": 'fdr_tsbky'
        }

        self.stat_test = test_method_to_param.get(stat_test, 'fisher')
        self.stat_correction = correction_method_to_param.get(
            stat_correction, 'fdr_bh')

    # --- Public Methods ---
    def perform_pea(self) -> pd.DataFrame | None:
        """Perform the pathway enrichment analysis with retries on failure.

        Returns:
            pd.DataFrame | None: DataFrame with enrichment results or None if failed.
        """

        if not self.is_running:
            return None

        self.enr = self._run_enrichment_with_retries()
        if self.enr is None:
            self.main_app.add_log_line(
                "Error, the enrichment analysis failed.", mode="WARNING")
            return None

        return self._process_results()

    # --- Private Methods ---
    def _run_enrichment_with_retries(self) -> pd.DataFrame | None:
        """Run the enrichment analysis with retry logic.

        Returns:
            pd.DataFrame | None: DataFrame with enrichment results or None if all attempts fail.
        """
        for attempt in range(1, self.max_retries + 1):
            # print(f"Attempt {attempt}...")

            if not self.is_running:
                print("Task stopped before processing.")
                return None

            try:
                time.sleep(1)
                return ora(
                    gene_list=self.gene_list,
                    library_name=self.gene_sets,
                    test=self.stat_test,
                    correction=self.stat_correction
                )
            except Exception as e:
                print(f"Attempt {attempt} failed: {e}")
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay)
                else:
                    return None

    def _process_results(self) -> pd.DataFrame | None:
        """Process and filter the enrichment results.
        Returns:
            pd.DataFrame | None: Processed DataFrame with filtered enrichment
            results or None if no results.
        """
        if not self.is_running or self.enr is None:
            self.main_app.add_log_line(
                "Task stopped before processing.", mode="WARNING")
            return None

        df = self.enr.copy()
        if df.empty:
            self.main_app.add_log_line(
                "No significant pathways found, try selecting different gene sets or adjusting the parameters.",
                mode="INFO")
            return None

        # Rename adjusted_p_value to Adjusted P-value to match self.sort_by
        df.rename(
            columns={"adjusted_p_value": "Adjusted P-value"}, inplace=True)

        # Apply cutoff filter
        df = df[df["Adjusted P-value"] <= self.cutoff]
        if df.empty:
            print("No pathways passed the cutoff filter.")
            return None

        sort_column = self.sort_by if self.sort_by in df.columns else "Adjusted P-value"
        df = df.sort_values(by=sort_column)

        self.results_df = df.reset_index(drop=True)

        return self.results_df
