"""Module to retrieve article metadata and PubTator annotations using PubMed and PMC IDs."""

# --- Standard Library Imports ---
from typing import Any

# --- Local Imports ---
from app.api_utils.pmc_pmid_utils import fetch_pmc_ids
from app.api_utils.pubmed_retrieval import get_pubmed_metadata
from app.api_utils.pubtator_retrieval import (
    batch_fetch_pubtator_content_from_pmc,
    batch_fetch_pubtator_content_from_pubmed,
)

# --- Type Aliases ---
PubtatorKey = tuple[str, str | None]

# --- Public Functions ---


def get_metadata_and_pubtator_data(
    main_app: Any,
    pubmed_ids: list[str] | None = None,
    email: str | None = None,
    api_key: str | None = None,
) -> dict[str, dict[str, dict]]:
    """
    Retrieve article metadata and PubTator annotations for a list of PubMed IDs.

    Workflow:
        1) Map PubMed IDs to PMC IDs.
        2) Fetch PubMed metadata for the articles.
        3) Fetch PubTator annotations using PMC IDs where available.
        4) For entries without PMC-derived annotations, attempt PubMed-derived annotations.
        5) Return a dict keyed by PubMed ID containing {"metadata", "pubtator_content"}.

    Args:
        pubmed_ids (list[str] | None): PubMed IDs to retrieve data for.
        email (str | None): Contact email for NCBI API usage.
        api_key (str | None): NCBI API key for increased rate limits.

    Returns:
        dict[str, dict[str, dict]]: { pmid: {"metadata": dict, "pubtator_content": dict}, ... }
    """
    # Avoid mutable default list
    if pubmed_ids is None:
        pubmed_ids: list[str] = []

    # Handle empty input
    if not pubmed_ids:
        return {}

    # Map PubMed IDs to PMC IDs
    pm_to_pmc_ids: dict[str, str | None] = fetch_pmc_ids(
        main_app=main_app,
        pubmed_ids=[str(id) for id in pubmed_ids],
        email=email,
        api_key=api_key,
    )

    # == METADATA ==
    metadata_dict: dict[str, dict] = get_pubmed_metadata(pm_to_pmc_ids)

    # == PubTator Content with ANNOTATIONS ==
    pubtator_content_dict: dict[PubtatorKey, dict] = {}
    pmc_ids: list[str] = []

    for pm_id, pmc_id in pm_to_pmc_ids.items():
        # Initialize the per-(pm_id, pmc_id) entry
        pubtator_content_dict[(pm_id, pmc_id)] = {}
        if pmc_id is not None:
            pmc_ids.append(pmc_id)

    # Fetch annotations for PMC IDs
    pmc_derived_annotations: dict[str, dict] = batch_fetch_pubtator_content_from_pmc(
        main_app, pmc_ids)

    # Add PMC-derived annotations where available
    # otherwise, collect PubMed IDs to fetch from PubMed
    pubmed_ids_for_pubtator_fetch: list[str] = []
    for pm_id, pmc_id in list(pubtator_content_dict.keys()):
        if pmc_id is not None and pmc_id in pmc_derived_annotations:
            pubtator_content_dict[(pm_id, pmc_id)
                                  ] = pmc_derived_annotations.get(pmc_id, {})
        else:
            pubmed_ids_for_pubtator_fetch.append(pm_id)

    # Otherwise, try fetching annotations from PubMed IDs
    pubmed_derived_annotations: dict[str, dict] = batch_fetch_pubtator_content_from_pubmed(
        main_app, pubmed_ids_for_pubtator_fetch
    )

    # Add annotations to pubtator_content_dict
    for pm_id, pmc_id in list(pubtator_content_dict.keys()):
        if pm_id in pubmed_derived_annotations:
            pubtator_content_dict[(pm_id, pmc_id)
                                  ] = pubmed_derived_annotations.get(pm_id, {})

    # Combine metadata and annotations
    retrieved_metadata_and_pubtator_content: dict[str, dict[str, dict]] = {}

    for (pm_id, pmc_id), _ in pubtator_content_dict.items():
        retrieved_metadata_and_pubtator_content[pm_id] = {
            "metadata": metadata_dict.get(str(pm_id), {}),
            "pubtator_content": pubtator_content_dict.get((pm_id, pmc_id), {}),
        }

    return retrieved_metadata_and_pubtator_content
