"""Module to fetch PubMed metadata for articles using PubMed IDs."""

# --- Standard Library Imports ---
import xml.etree.ElementTree as ET

# --- Third Party Imports ---
import requests

# --- Constants ---
BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

# --- Public Functions ---


def get_pubmed_metadata(pm_to_pmc_ids: dict[str, str | None]) -> dict[str, dict]:
    """
    Retrieve PubMed metadata for a set of PubMed IDs.

    Args:
        pm_to_pmc_ids: Dictionary mapping PubMed IDs to PMC IDs (if available).

    Returns:
        dict: Dictionary mapping PubMed IDs to their metadata.
    """

    # Convert list of IDs to a comma-separated string
    id_string = ",".join(map(str, pm_to_pmc_ids.keys()))

    # Fetch metadata using esummary (batch retrieval)
    summary_url = f"{BASE_URL}esummary.fcgi?db=pubmed&id={id_string}&retmode=json"
    summary_response = requests.get(summary_url, timeout=30)
    summary_data = summary_response.json()

    # Fetch details using efetch (for more fields including abstract)
    fetch_url = f"{BASE_URL}efetch.fcgi?db=pubmed&id={id_string}&retmode=xml"
    fetch_response = requests.get(fetch_url, timeout=30)

    # Parse XML response
    root = ET.fromstring(fetch_response.content)

    # Dictionary to store metadata for each PubMed ID
    metadata_dict: dict[str, dict] = {}

    for pubmed_id, pmc_id in pm_to_pmc_ids.items():
        result: dict = summary_data.get("result", {}).get(str(pubmed_id), {})

        # Initialize metadata dictionary for the article
        metadata = {
            "id": result.get("uid", ""),
            "pubmed_id": pubmed_id,
            "pmc_id": pmc_id,
            "title": result.get("title", ""),
            "authors": [],
            "journal": result.get("source", ""),
            "year": result.get("pubdate", "").split(" ")[0] if result.get("pubdate") else None,
            "keywords": [],
            "doi": None,
            "mesh_terms": [],
            "chemical_list": [],
            "references": [],
            "citations": [],
            "abstract": None,
            "full_text": None,
            "license": None,
            "publication_type": [],
            "language": None,
            "country": None,
            "institution": None,
            "funding": [],
            "biomedical_entities": []
        }

        # Extract authors safely
        if "authors" in result and isinstance(result["authors"], list):
            metadata["authors"] = [author.get("name", "").strip()
                                   for author in result["authors"]
                                   if "name" in author]

        # Find the corresponding XML entry safely
        article = None
        for art in root.findall(".//PubmedArticle"):
            pmid_element = art.find(".//PMID")
            if pmid_element is not None and pmid_element.text == str(pubmed_id):
                article = art
                break

        if article is not None:
            article_data = article.find(".//Article")

            # Extract Abstract safely
            abstract_texts = article.findall(".//Abstract/AbstractText")
            if abstract_texts:
                metadata["abstract"] = " ".join([text.text.strip()
                                                 for text in abstract_texts
                                                 if text.text]
                                                )

            # DOI
            doi_element = article.find(".//ArticleId[@IdType='doi']")
            metadata["doi"] = doi_element.text.strip(
            ) if doi_element is not None else None

            # Language
            lang_element = article_data.find(
                "Language") if article_data is not None else None
            metadata["language"] = lang_element.text.strip(
            ) if lang_element is not None else None

            # Publication Type
            metadata["publication_type"] = [pt.text.strip()
                                            for pt in article.findall(".//PublicationType")
                                            if pt.text]

            # Extract Mesh Terms safely
            mesh_terms = article.findall(".//MeshHeading")
            metadata["mesh_terms"] = [mesh.find(".//DescriptorName").text.strip()
                                      for mesh in mesh_terms]

            # Extract Chemical List safely
            chemicals = article.findall(".//Chemical")
            metadata["chemical_list"] = [chem.find(".//NameOfSubstance").text.strip()
                                         for chem in chemicals]

            # Extract Country
            country_element = article.find(
                ".//MedlineCitation/MedlineJournalInfo/Country")
            metadata["country"] = country_element.text.strip(
            ) if country_element is not None else None

            # Extract Institution
            institution_element = article.find(
                ".//MedlineCitation/Article/AuthorList/Author/Affiliation")
            metadata["institution"] = institution_element.text.strip(
            ) if institution_element is not None else None

            # Extract Funding
            funding_elements = article.findall(".//Grant")
            metadata["funding"] = [f.text.strip()
                                   for f in funding_elements if f.text]

            # Extract keywords
            keyword_elements = article.findall(".//Keyword")
            metadata["keywords"] = [kw.text.strip()
                                    for kw in keyword_elements if kw.text]

            # Extract pmc_id
            if pmc_id is None:
                pmc_id_element = article.find(".//ArticleId[@IdType='pmc']")
                metadata["pmc_id"] = pmc_id_element.text.strip(
                ) if pmc_id_element is not None else None

        metadata_dict[str(pubmed_id)] = metadata

    return metadata_dict
