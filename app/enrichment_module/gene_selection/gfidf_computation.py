"""Computes GF-IDF scores for genes based on their annotations in articles"""

# --- Standard Library Imports ---
import math
import sqlite3

# --- Local Imports ---
from app.utils import resource_path

# --- Constants ---
# get_total_pubtator_articles_with_genes()
TOTAL_PUBTATOR_ARTICLE_COUNT_WITH_GENES = 8562517


# --- Public Functions ---
def compute_gfidf(gene_data: list[tuple[str, str, int, str, list[str]]]) -> dict[str, float]:
    """
    Compute the GF-IDF score for a given gene.
    input is gene_data, which is a list of 4 elements: 
    [entrez_id (gene identifier), gene_symbol, num_annotations, tax_id]

    Args:
    - freq_g_A: Number of mentions of gene g across all articles in A.
    - freq_G_A: Total number of gene mentions across all articles in A.
    - size_P: Total number of articles in the PubTator3 database P with at least
    one gene annotation.
    - freq_g_P: Number of articles in P mentioning gene g at least once.

    Returns:
    - GF-IDF score.
    """

    entrez_id_to_gfidf_map = {}

    # Total articles with at least one gene annotation
    total_articles = TOTAL_PUBTATOR_ARTICLE_COUNT_WITH_GENES
    # Total gene mentions across all articles
    freq_G_A = sum([x[2] for x in gene_data])

    # Avoid computation if there are no gene mentions
    if freq_G_A == 0:
        return {}

    # Compute GF-IDF for each gene
    for (entrez_id, _, num_annotations, _, _) in gene_data:
        gene_identifier = entrez_id
        freq_g_A = num_annotations
        # Get the actual count for this gene
        freq_g_P = _get_identifier_count(gene_identifier)

        # Avoid division by zero
        term_frequency = freq_g_A / freq_G_A if freq_G_A != 0 else 0

        # IDF calculation to prevent negative values
        inverse_document_frequency = math.log(
            (total_articles + 1) / (freq_g_P + 1))  # Ensuring positive IDF

        entrez_id_to_gfidf_map[entrez_id] = round(
            term_frequency * inverse_document_frequency, 3)

    return entrez_id_to_gfidf_map


# --- Private Functions ---
def _get_identifier_count(identifier: str) -> int:
    """Fetches the count of a given Identifier from the small SQLite3 database.

    Args:
        identifier (str): The gene identifier (e.g., Entrez ID).
    Returns:
        int: The count of articles mentioning the identifier.
    """
    conn = sqlite3.connect(resource_path(
        "assets/external_data/pubtator_count.db"))
    cursor = conn.cursor()

    cursor.execute(
        "SELECT Count FROM IdentifierCounts WHERE Identifier = ?", (identifier,))
    result = cursor.fetchone()

    conn.close()

    # Return count if found, otherwise return 0
    return result[0] if result else 0


'''
Note: The function get_total_pubtator_articles_with_genes() is not used in the current implementation. 
It was used to determine the total number of articles with gene annotations initially, 
but this value is now hardcoded as TOTAL_PUBTATOR_ARTICLE_COUNT_WITH_GENES for efficiency.
This represents a one-time computation to avoid repeated database access (PubTator status as of December 2024)
def get_total_pubtator_articles_with_genes(): # should return 8562517
    conn = sqlite3.connect(resource_path("assets/external_data/pubtator_doc_count.db"))
    cursor = conn.cursor()

    # count lines in table IDCounts
    cursor.execute("SELECT COUNT(*) FROM IDCounts")
    result = cursor.fetchone()

    conn.close()

    return result[0] if result else 0
'''
