"""Utility functions for the enrichment module"""

# --- Third Party Imports ---
import json

# --- Local Imports ---
from app.utils import resource_path


# --- Public Functions ----
def load_tax2name() -> dict[str, str]:
    """Loads the Tax ID to organism name mapping from a JSON file.

    Returns:
        A dictionary mapping Tax IDs (as strings) to organism names.
    """
    # Load JSON file
    with open(resource_path("assets/external_data/gene2organism_mapping/tax2name.json"),
              "r", encoding="utf-8") as file:
        data = json.load(file)  # Load JSON into a dictionary

    return data
