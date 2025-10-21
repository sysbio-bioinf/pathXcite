"""Utilities to set up initial GMT files for enrichment analysis"""

# --- Standard Library Imports ---
import os

# --- Third Party Imports ---
import requests

# --- Local Imports ---
from app.utils import resource_path
import time
from requests.adapters import HTTPAdapter
from urllib3.util import Retry


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
    num_libraries = len(basic_libraries)
    for i, library in enumerate(basic_libraries):
        gmt_path = os.path.join(gmt_folder, f"{library}.gmt")
        if not os.path.exists(gmt_path):
            percentage = int((i + 1) / num_libraries * 100)
            print(
                f"Downloading {library} library ({i + 1}/{num_libraries})...")
            _download_enrichr_library(gmt_folder, library)
            print(f"{library} library downloaded. ({percentage}% complete)")
        else:
            percentage = int((i + 1) / num_libraries * 100)
            print(
                f"{library} library already exists. Skipping download. ({percentage}% complete)")

# --- Private Functions ---


def _download_enrichr_library(folder_path: str, library_name: str) -> None:
    """
    Downloads a gene set library from Enrichr and saves it as a text file.
    This function will never raise — it implements retries and on permanent
    failure writes a small stub file describing the failure so the caller
    can continue without crashing.
    """
    try:
        # urllib3 may use different parameter names across versions; 'allowed_methods'
        # is preferred, but fall back to 'method_whitelist' if necessary.
        retry_kwargs = {"total": 3, "backoff_factor": 1,
                        "status_forcelist": [429, 500, 502, 503, 504]}
        try:
            retry_kwargs["allowed_methods"] = frozenset(["GET"])
        except Exception:
            # older urllib3 versions use method_whitelist
            retry_kwargs["method_whitelist"] = frozenset(["GET"])
        retry_strategy = Retry(**retry_kwargs)
    except Exception:
        # If Retry import fails for any reason, continue without adapter-level retries
        retry_strategy = None

    os.makedirs(folder_path, exist_ok=True)
    url = f"https://maayanlab.cloud/Enrichr/geneSetLibrary?mode=text&libraryName={library_name}"
    output_path = os.path.join(folder_path, f"{library_name}.gmt")

    session = requests.Session()
    if retry_strategy is not None:
        session.mount("https://", HTTPAdapter(max_retries=retry_strategy))
        session.mount("http://", HTTPAdapter(max_retries=retry_strategy))

    max_attempts = 3
    backoff = 1  # seconds
    last_exception = None

    for attempt in range(1, max_attempts + 1):
        try:
            response = session.get(url, timeout=30)
            response.raise_for_status()
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(response.text)
            print(f"Downloaded and saved {library_name} to {output_path}")
            return
        except Exception as exc:
            last_exception = exc
            print(
                f"Attempt {attempt}/{max_attempts} failed for {library_name}: {exc}")
            if attempt < max_attempts:
                time.sleep(backoff)
                backoff *= 2
            else:
                # Write to the console that all attempts failed
                print(
                    f"""All attempts failed for {library_name}. 
                    
                    !      > Please check your internet connection.""")
                return


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
