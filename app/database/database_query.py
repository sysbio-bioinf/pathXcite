"""Provides functions to query PubMed data from the local database"""

# --- Standard Library Imports ---
import json
import sqlite3
from collections import defaultdict

# --- Local Imports ---
from app.enrichment_module.enrichment_utils import load_tax2name
from app.setup_utils.setup_utils import map_gene_ids_to_taxids
from app.utils import resource_path

# --- Constants ---
TAX2NAME_MAP: dict[str, str] = load_tax2name()

# --- Public Functions ---


def get_pubmed_ids_from_db(db_path: str) -> list[str]:
    """
    Retrieve all PubMed IDs from the articles table in the database.

    Args:
        db_path (str): Path to the SQLite database. 

    Returns:
        list: A list of PubMed IDs as strings.
    """
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''SELECT pubmed_id FROM articles''')
    pubmed_ids: list[str] = c.fetchall()
    conn.close()
    return [pubmed_id[0] for pubmed_id in pubmed_ids]


def retrieve_document_data(pubmed_id: str, db_path: str) -> dict:
    """
    Retrieve article metadata, entities, and annotations for a given PubMed ID.

    Args:
        pubmed_id (str): The PubMed ID of the article to retrieve.
        db_path (str): Path to the SQLite database.

    Returns:
        dict: A dictionary containing article metadata, entities, and annotations.
    """
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''SELECT * FROM articles WHERE pubmed_id=?''', (pubmed_id,))
    article: tuple = c.fetchone()

    article = {
        'pubmed_id': article[0],
        'pmc_id': article[1],
        'title': article[2],
        'authors': json.loads(article[3]),
        'journal': article[4],
        'year': article[5],
        'keywords': json.loads(article[6]),
        'doi': article[7],
        'mesh_terms': json.loads(article[8]),
        'abstract': article[10],
        'publication_type': json.loads(article[11])
    }

    c.execute('''SELECT * FROM annotations WHERE pubmed_id=?''', (pubmed_id,))
    annotations_document: list[tuple] = c.fetchall()

    entity_ids_document = list(set([annotation[1] for annotation in annotations_document
                                    if annotation[1] is not None and annotation[1] != "None"
                                    and annotation[1] != "-"
                                    and annotation[1] != ""
                                    and str.isdigit(annotation[1])]))
    gene2organism_map_path = resource_path(
        "assets/external_data/gene2organism_mapping")
    mapped_gene_ids = map_gene_ids_to_taxids(
        gene2organism_map_path, entity_ids_document)
    entity_ids_to_tax = {str(k): v for k, v in mapped_gene_ids.items()}

    # fetch entity entries from entities table where entity id in entity_ids_document
    gene_entities_document: list[tuple] = []
    gene_entity_ids_to_symbol: dict[str, str] = {}
    for entity_id in entity_ids_document:
        c.execute(
            '''SELECT * FROM entities WHERE entity_id=? and biotype=?''', (entity_id, 'gene'))
        entity: tuple = c.fetchone()
        if entity is not None and entity != "None" and entity != "-" and entity != "":
            gene_entities_document.append(entity)
            gene_entity_ids_to_symbol[entity[0]] = entity[5]
    conn.close()

    # filter annotations to only contain annotations where the entity id is in gene_entity_ids
    annotations_document = [annotation for annotation in annotations_document
                            if annotation[1] in gene_entity_ids_to_symbol]
    entity_symbol_to_annotations = defaultdict(list)

    # selected_species_tax = [str(species.split(" ")[-1][1:-1]) for species in selected_species]

    for annotation in annotations_document:
        if annotation[1] is not None:
            tax_id: str = entity_ids_to_tax.get(annotation[1], None)
            # if str(tax_id) in selected_species_tax:
            if tax_id is None:
                continue
            else:
                tax_id = f"{tax_id, TAX2NAME_MAP.get(str(tax_id), 'Unknown')}"
                # annotation[1] is the entity id, gene_entity_ids_to_symbol[annotation[1]]
                # is the gene symbol
                # is the key unique? yes, because it is a combination of entity id and tax id
                # so entity symbol to annotations is a dictionary where the keys are tuples of
                # (entity id, gene symbol, tax id) and the values are lists of annotations
                # does it truly capture all annotations for a given entity id and tax id?
                # yes, because we are iterating over all annotations and adding them to the
                # list for the corresponding key
                key: tuple = (
                    annotation[1], gene_entity_ids_to_symbol[annotation[1]], tax_id)
                entity_symbol_to_annotations[key].append({
                    'accession': annotation[2],
                    'tax_id': tax_id,
                    'offset_start': annotation[3],
                    'length': annotation[4],
                    'text': annotation[5],
                    'pubmed_id': annotation[6],
                    'passage_number': annotation[7]
                })

    article.update({'entities': entity_ids_document,
                   'annotations': entity_symbol_to_annotations})

    return article


def get_article_count(db_path: str) -> int:
    """
    Returns the number of entries in the 'articles' table of a valid database.

    Args:
        db_path (str): Path to the SQLite database.

    Returns:
        int: Number of articles in the database.
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM articles;")
        article_count: int = cursor.fetchone()[0]

        return article_count

    except sqlite3.Error:
        return 0  # Return 0 if there's an error

    finally:
        conn.close()


def get_all_pubmed_and_pmc_ids(db_path: str) -> list[tuple[str, str | None]]:
    """
    Retrieves all PubMed and PMC IDs from the articles table in the database.

    Args:
        db_path (str): Path to the SQLite database.

    Returns:
        list: A list of tuples containing PubMed and PMC IDs.
    """
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''SELECT pubmed_id, pmc_id FROM articles''')
    pubmed_pmc_ids: list[tuple[str, str | None]] = c.fetchall()
    conn.close()
    return pubmed_pmc_ids
