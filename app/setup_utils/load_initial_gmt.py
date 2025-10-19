"""Utilities to set up initial GMT files for enrichment analysis"""

# --- Standard Library Imports ---
import os

# --- Third Party Imports ---
import requests

# --- Local Imports ---
from app.utils import resource_path


# --- Public Functions ---

def run_initial_gmt_setup() -> None:
    """
    Ensures the necessary folder structure and downloads the Enrichr library.
    """
    base_folder = resource_path("assets/external_data")
    # Define required folders
    gmt_folder = os.path.join(base_folder, "gmt_files")

    # Ensure folders exist
    _ensure_folder_exists(gmt_folder)

    basic_libraries = ["BioPlanet_2019", "DisGeNET", "DrugMatrix",
                       "GO_Biological_Process_2025",
                       "GO_Cellular_Component_2025", "GO_Molecular_Function_2025",
                       "KEGG_2021_Human",
                       "KEGG_2019_Mouse", "OMIM_Disease", "Panther_2016",
                       "Reactome_Pathways_2024", "WikiPathways_2024_Human"]
    # Download Enrichr library
    # check if the basic gmt files already exist
    for library in basic_libraries:
        gmt_path = os.path.join(gmt_folder, f"{library}.gmt")
        if not os.path.exists(gmt_path):
            _download_enrichr_library(gmt_folder, library)

# --- Private Functions ---


def _download_enrichr_library(folder_path: str, library_name: str) -> None:
    """
    Downloads a gene set library from Enrichr and saves it as a text file.

    Args:
        folder_path (str): The directory where the file will be saved.
        library_name (str): The name of the Enrichr library (e.g., "GeneSigDB").
    """
    # Ensure folder exists
    os.makedirs(folder_path, exist_ok=True)

    # Define URL and destination path
    url = f"https://maayanlab.cloud/Enrichr/geneSetLibrary?mode=text&libraryName={library_name}"
    output_path = os.path.join(folder_path, f"{library_name}.gmt")

    # Download the data
    response = requests.get(url, timeout=400)
    response.raise_for_status()  # Raise error if download failed

    # Save the file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(response.text)


def _ensure_folder_exists(folder_path: str) -> None:
    """
    Checks if a folder exists at the given path. 
    If not, it creates the folder.

    Args:
        folder_path (str): The path of the folder to check/create.
    """
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        print(f"Folder created: {folder_path}")
    else:
        print(f"Folder already exists: {folder_path}")
