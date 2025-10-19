"""Module to fetch Pubtator annotations for articles using PMC or PubMed IDs."""

# --- Standard Library Imports ---
from typing import Any

# --- Third Party Imports ---
import requests

# --- Constants ---
PUBTATOR_URL = "https://www.ncbi.nlm.nih.gov/research/pubtator3-api/publications"

# --- Public Functions ---


def batch_fetch_pubtator_content_from_pmc(main_app: Any,
                                          pmc_ids: list[str] | None,
                                          batch_size: int = 100) -> dict[str, dict]:
    """
    Retrieve Pubtator annotations for a set of PMC IDs.

    Args:
        main_app: Main application instance for logging.
        pmc_ids: List of PMC IDs to retrieve annotations for.
        batch_size: Number of PMCIDs to check per request (default is 100).

    Returns:
        dict: Dictionary mapping PMC IDs to their Pubtator content.
    """
    # Avoid mutable default list
    if pmc_ids is None:
        pmc_ids: list[str] = []

    if not pmc_ids:
        return {}

    base_url = f"{PUBTATOR_URL}/pmc_export/biocjson"
    content_by_id: dict[str, dict] = {}

    pmc_ids_list = list(pmc_ids)  # Convert dict_values to list

    # Process in batches
    for i in range(0, len(pmc_ids_list), batch_size):
        batch_ids = pmc_ids_list[i:i + batch_size]
        params = {"pmcids": ",".join(map(str, batch_ids))}
        response = requests.get(base_url, params=params, timeout=30)

        try:
            data = response.json()
        except ValueError:
            main_app.add_log_line(
                f"Invalid JSON response for batch {batch_ids}")
            continue

        if "PubTator3" not in data:
            main_app.add_log_line(
                f"Unexpected response format for batch {batch_ids}")
            continue

        if response.status_code != 200:
            main_app.add_log_line(
                f"Error fetching content for PMC IDs {batch_ids}: {response.status_code}")
            continue

        data = response.json()

        # Store content by PMC ID
        for doc in data.get("PubTator3", []):
            pmcid = doc.get("pmcid", "")
            content_by_id[pmcid] = doc

    return content_by_id


def batch_fetch_pubtator_content_from_pubmed(main_app: Any,
                                             pubmed_ids: list[str] | None,
                                             batch_size: int = 100) -> dict[str, dict]:
    """
    Retrieve Pubtator annotations for a set of PubMed IDs.

    Args:
        main_app: Main application instance for logging.
        pubmed_ids: List of PubMed IDs to retrieve annotations for.
        batch_size: Number of PMIDs to check per request (default is 100).

    Returns:
        dict: Dictionary mapping PubMed IDs to their Pubtator content.
    """

    # Avoid mutable default list
    if pubmed_ids is None:
        pubmed_ids: list[str] = []

    if not pubmed_ids:
        return {}

    base_url = f"{PUBTATOR_URL}/export/biocjson"
    content_by_id: dict[str, dict] = {}

    pubmed_ids_list = list(pubmed_ids)  # Convert dict_values to list

    # Process in batches
    for i in range(0, len(pubmed_ids_list), batch_size):
        batch_ids = pubmed_ids_list[i:i + batch_size]
        params = {"pmids": ",".join(map(str, batch_ids))}
        response = requests.get(base_url, params=params, timeout=30)

        try:
            data = response.json()
        except ValueError:
            main_app.add_log_line(
                f"Invalid JSON response for batch {batch_ids}")
            continue

        if "PubTator3" not in data:
            main_app.add_log_line(
                f"Unexpected response format for batch {batch_ids}")
            continue

        if response.status_code != 200:
            main_app.add_log_line(
                f"Error fetching content for PubMed IDs {batch_ids}: {response.status_code}")
            continue

        data = response.json()

        # Store content by PubMed ID
        for doc in data.get("PubTator3", []):
            pmid = doc.get("pmid", "")
            content_by_id[pmid] = doc

    return content_by_id
