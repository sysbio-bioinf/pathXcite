"""Implements Over-Representation Analysis (ORA) computation for gene sets"""

# --- Standard Library Imports ---
import os
from concurrent.futures import ThreadPoolExecutor
from functools import partial

# --- Third-Party Imports ---
import numpy as np
import pandas as pd
from scipy.stats import fisher_exact, hypergeom
from statsmodels.stats.multitest import multipletests

# --- Local Imports ---
from app.utils import resource_path

# --- Constants ---
with open(resource_path("assets/external_data/background_genes.txt"), 'r',
          encoding="utf-8") as f:
    BACKGROUND_GENES: set[str] = {line.strip() for line in f}


# --- Public Functions ---
def ora(
    gene_list: set[str],
    library_name: str = "WikiPathways_2024_Human",
    background_genes: set[str] | None = None,
    test: str = 'fisher',
    correction: str = 'fdr_bh',
    n_jobs: int = 8
) -> pd.DataFrame:
    """
    Perform Over-Representation Analysis (ORA) on a list of genes.

    Args:
        gene_list: Set of genes for enrichment analysis.
        library_name: The gene set library to use (default: "WikiPathways_2024_Human").
        background_genes: Set of background genes (default: predefined background).
        test: Statistical test to use ('fisher' or 'hypergeom', default: 'fisher').
        correction: Multiple testing correction method (default: 'fdr_bh').
        n_jobs: Number of parallel jobs to run (default: 8).

    Returns:
        pd.DataFrame: DataFrame with enrichment results.
    """
    gene_list: set[str] = {gene.upper() for gene in gene_list}
    if background_genes is None:
        # use a fresh set so calls never share state
        background_genes = BACKGROUND_GENES.copy()
    gmt_path: str = resource_path(
        f"assets/external_data/gmt_files/{library_name}.gmt")

    if not os.path.exists(gmt_path):
        print(f"GMT file for {library_name} not found at {gmt_path}")
        return pd.DataFrame()

    gene_sets: dict[str, set[str]] = _parse_gmt(gmt_path)

    # Pre-filter gene sets
    filtered_sets = {
        term: genes for term, genes in gene_sets.items()
        if len(genes & gene_list & background_genes) > 0
    }

    num_background = len(background_genes)
    num_genes = len(gene_list)

    # Threaded execution for lower overhead
    process = partial(
        _process_term,
        gene_list=gene_list,
        background_genes=background_genes,
        test=test,
        num_background=num_background,
        num_genes=num_genes
    )

    with ThreadPoolExecutor(max_workers=n_jobs) as executor:
        results = list(executor.map(
            lambda kv: process(*kv), filtered_sets.items()))

    # Filter out None results
    results = [r for r in results if r is not None]

    if not results:
        return pd.DataFrame()

    df = pd.DataFrame(results)

    # Multiple testing correction
    # Adjusted P-value: corrected for multiple comparisons
    df['Adjusted P-value'] = multipletests(df['P-value'], method=correction)[1]

    return df.sort_values('P-value').reset_index(drop=True)

# --- Private Functions ---


def _parse_gmt(gmt_path: str) -> dict[str, set[str]]:
    """
    Parse a GMT file and return a dictionary of gene sets.

    Args:
        gmt_path: Path to the GMT file.

    Returns:
        A dictionary mapping gene set (term) names to sets of genes.
    """
    gene_sets: dict[str, set[str]] = {}
    with open(gmt_path, 'r', encoding="utf-8") as file:
        for line in file:
            parts = line.strip().split('\t')
            if len(parts) >= 3:
                gene_sets[parts[0]] = {gene.upper().split(",")[0]
                                       for gene in parts[2:]}

    return gene_sets


def _compute_z_score(a: int, term_size: int, query_size: int, bg_size: int) -> float:
    """
    Compute the Z-score for a given term. This score indicates how much the observed overlap
    deviates from the expected overlap under a hypergeometric distribution.

    Args:
        a: Number of genes in the intersection of the gene list and the term.
        term_size: Total number of genes in the term.
        query_size: Total number of genes in the gene list.
        bg_size: Total number of genes in the background.

    Returns:
        The Z-score as a float.
    """
    # if bg_size <= 1:
    #    ("Background size must be greater than 1.")

    expected = (term_size / bg_size) * query_size
    variance = (term_size * (bg_size - term_size) *
                query_size * (bg_size - query_size)) / (bg_size**2 * (bg_size - 1))

    if variance <= 0:
        return 0.0

    return (a - expected) / np.sqrt(variance)


def _process_term(term: str, term_genes: set[str], gene_list: set[str],
                  background_genes: set[str], test: str, num_background: int,
                  num_genes: int) -> dict | None:
    """
    Process a single term for ORA.

    Args:
        term: The name of the term.
        term_genes: Set of genes in the term.
        gene_list: Set of genes in the input gene list.
        background_genes: Set of genes in the background.
        test: Statistical test to use ('fisher' or 'hypergeom').
        M: Total number of genes in the background.
        N: Total number of genes in the gene list.

    Returns:
        A dictionary with enrichment results for the term, or None if no genes overlap.
    """
    term_genes_in_bg = term_genes & background_genes
    genes_in_term = gene_list & term_genes_in_bg
    # Calculate contingency table values
    # a: overlap count
    # b: term only
    # c: gene list only
    # d: neither

    a = len(genes_in_term)
    if a == 0:
        return None

    b = len(term_genes_in_bg) - a
    c = len(gene_list) - a
    d = num_background - a - b - c

    if test == 'fisher':
        _, p_value = fisher_exact([[a, b], [c, d]], alternative='greater')
    elif test == 'hypergeom':
        p_value = hypergeom.sf(a - 1, num_background,
                               len(term_genes_in_bg), num_genes)
    else:
        raise ValueError("Invalid test: must be 'fisher' or 'hypergeom'")

    # -- Calculate additional statistics
    # Odds Ratio: this defines the strength of association between gene list and term
    odds_ratio: float = (a * d / (b * c)) if b > 0 and c > 0 else np.inf
    # Compute Z-score: measures deviation from expected overlap
    z: float = _compute_z_score(
        a, len(term_genes_in_bg), num_genes, num_background)
    # Combined Score: integrates p-value and Z-score
    combined_score: float = -np.log10(p_value) * z if p_value > 0 else np.inf

    return {
        'Term': term,
        'Genes': ';'.join(sorted(genes_in_term)),
        'Overlap': f"{a}/{len(term_genes_in_bg)}",
        'Count': a,
        'Term Size': len(term_genes_in_bg),
        'Query Size': num_genes,
        'Background Size': num_background,
        'P-value': p_value,
        'Odds Ratio': odds_ratio,
        'Z-Score': z,
        'Combined Score': combined_score,
        'Adjusted P-value': None  # To be filled later
    }
