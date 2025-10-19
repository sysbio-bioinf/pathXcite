"""Module to convert between PubMed IDs (PMIDs) and PubMed Central IDs (PMCIDs)
    using NCBI ID converter API."""

# --- Standard Library Imports ---
from __future__ import annotations

import time
from typing import Any

# --- Third Party Imports ---
import requests

# --- Constants ---
BASE_URL = "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/"

# --- Public Functions ---


def fetch_pmc_ids(
        main_app: Any,
        pubmed_ids: list[str] | None,
        batch_size: int = 175,
        delay: float = 0.1,
        max_retries: int = 5,
        api_key: str | None = None,
        email: str | None = None,
        tool: str = "pathXcite") -> dict[str, str | None]:
    """
    Fetch PMC IDs corresponding to given PubMed IDs (PMIDs) using 
    NCBI's ID converter API with robust retry handling.

    Args:
        pubmed_ids: List of PubMed IDs to check for associated PMC IDs.
        batch_size: Number of PMIDs to check per request (default is 175).
        delay: Initial delay in seconds between requests.
        max_retries: Maximum number of retry attempts in case of failure.
        api_key: Optional NCBI API key for increased rate limits.
        email: Contact email for API usage.
        tool: Tool name to identify API usage.

    Returns:
        dict: Dictionary mapping PMIDs to their corresponding PMC IDs (if available).
    """

    # Avoid mutable default list
    if pubmed_ids is None:
        pubmed_ids: list[str] = []

    # Handle empty input
    if not pubmed_ids:
        return {}

    pmc_mapping: dict[str, str | None] = {}

    # Clean pubmed_ids list
    pubmed_ids = [pmid.strip()
                  for pmid in pubmed_ids
                  if pmid is not None and str(pmid).strip() and pmid.strip().lower() != "none"]

    # Process in batches
    for i in range(0, len(pubmed_ids), batch_size):
        batch = pubmed_ids[i:i + batch_size]
        params = {
            "ids": ",".join(batch),
            "format": "json",
            "tool": tool
        }

        if api_key:
            params["api_key"] = api_key
        if email:
            params["email"] = email

        retries = 0
        while True:
            try:
                response = requests.get(BASE_URL, params=params, timeout=10)
                response.raise_for_status()  # Raise an error for bad status codes
                data = response.json()

                # Extract PMC IDs from the response
                for record in data.get("records", []):
                    pmid: str = record.get("pmid")
                    pmc: str | None = record.get("pmcid")
                    if pmid:
                        pmc_mapping[pmid] = pmc or None

                # Respect rate limits: shorter delay if API key is provided
                time.sleep(delay if api_key else 0.4)
                break  # Success, exit retry loop

            except requests.exceptions.RequestException as e:
                retries += 1
                if retries > max_retries:
                    main_app.add_log_line(
                        f"Max retries exceeded for batch starting at index {i}.")
                    break
                # Exponential backoff, max 60s
                wait_time = min(2 ** retries, 60)
                main_app.add_log_line(
                    f"Attempt {retries} failed: {e}. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)

    return pmc_mapping


def fetch_pmids(
        main_app: Any,
        pmc_ids: list[str] | None = None,
        batch_size: int = 100,
        delay: float = 0.3,
        max_retries: int = 5,
        api_key: str | None = None,
        email: str | None = None,
        tool: str = "pathXcite") -> dict[str, str | None]:
    """
    Fetch PubMed IDs (PMIDs) corresponding to given PubMed Central IDs (PMCIDs) 
    using NCBI's ID converter API with robust retry handling.

    Args:
        pmc_ids: List of PMC IDs to check for associated PubMed IDs.
        batch_size: Number of PMCIDs to check per request (default is 100).
        delay: Initial delay in seconds between requests.
        max_retries: Maximum number of retry attempts in case of failure.
        api_key: Optional NCBI API key for increased rate limits.
        email: Contact email for API usage.
        tool: Tool name to identify API usage.

    Returns:
        dict: Dictionary mapping PMCIDs to their corresponding PMIDs (if available).
    """

    # Avoid mutable default list
    if pmc_ids is None:
        pmc_ids: list[str] = []

    if not pmc_ids:
        return {}

    pmid_mapping: dict[str, str | None] = {}

    # Clean pmc_ids list
    pmc_ids = [pmc_id.strip()
               for pmc_id in pmc_ids
               if pmc_id is not None and str(pmc_id).strip() and pmc_id.strip().lower() != "none"]

    for i in range(0, len(pmc_ids), batch_size):
        batch = pmc_ids[i:i + batch_size]
        params = {
            "ids": ",".join(batch),
            "format": "json",
            "tool": tool
        }

        if api_key:
            params["api_key"] = api_key
        if email:
            params["email"] = email

        retries = 0
        while True:
            try:
                response = requests.get(BASE_URL, params=params, timeout=10)
                response.raise_for_status()  # Raise an error for bad status codes
                data = response.json()

                # Extract PMID IDs from the response
                for record in data.get("records", []):
                    pmc = record.get("pmcid")
                    pmid = record.get("pmid")
                    if pmc:
                        pmid_mapping[pmc] = pmid if pmid else None

                # Respect rate limits: shorter delay if API key is provided
                time.sleep(delay if api_key else 0.5)
                break  # Success, exit retry loop

            except requests.exceptions.RequestException as e:
                retries += 1
                if retries > max_retries:
                    main_app.add_log_line(
                        f"Max retries exceeded for batch starting at index {i}.")
                    break
                # Exponential backoff, max 60s
                wait_time = min(2 ** retries, 60)
                main_app.add_log_line(
                    f"Attempt {retries} failed: {e}. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)

    return pmid_mapping
