"""Provides functions to create the local database schema for PubMed data"""

# --- Standard Library Imports ---
import sqlite3

# --- Public Functions ---
# function to create a database


def create_database(db_path: str) -> None:
    """Create the database schema for storing PubMed data.

    Args:
        db_path (str): The file path where the SQLite database will be created.
    """
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE articles (
            pubmed_id TEXT PRIMARY KEY,
            pmc_id TEXT,
            title TEXT,
            authors TEXT,
            journal TEXT,
            year INTEGER,
            keywords TEXT,
            doi TEXT,
            mesh_terms TEXT,
            chemical_list TEXT,
            abstract TEXT,
            publication_type TEXT,
            language TEXT,
            country TEXT,
            institution TEXT,
            funding TEXT
        )
    """)

    c.execute("""
        CREATE TABLE passages (
            passage_id INTEGER PRIMARY KEY,
            pubmed_id TEXT,
            pmc_id TEXT,
            passage_number INTEGER,
            passage_text TEXT,
            section_type TEXT,
            type TEXT,
            offset INTEGER,
            relations TEXT
        )
    """)

    c.execute("""
        CREATE TABLE entities (
            entity_id TEXT PRIMARY KEY,
            type TEXT,
            database TEXT,
            normalized_id TEXT,
            biotype TEXT,
            name TEXT,
            accession TEXT
        )
    """)

    c.execute("""
        CREATE TABLE annotations (
            annotation_id INTEGER PRIMARY KEY,
            entity_id TEXT,
            accession TEXT,
            offset_start INTEGER,
            length INTEGER,
            text TEXT,
            pubmed_id TEXT,
            passage_number INTEGER
        )
    """)

    conn.commit()
    conn.close()


"""
# function to create a database

# the database will have the following tables:
# 1. articles: contains metadata about the articles
# 1a. pmc_id: primary key
# 1b. pubmed_id: foreign key
# 1c. title: text
# 1d. authors: text
# 1e. journal: text
# 1f. year: integer
# 1g. keywords: text
# 1h. doi: text
# 1i. mesh_terms: text
# 1j. chemical_list: text
# 1k. abstract: text
# 1l. publication_type: text
# 1m. language: text
# 1n. country: text
# 1o. institution: text
# 1p. funding: text

# 2. passages: contains the passages for each article
# 2a. passage_id: primary key
# 2b. pmc_id: foreign key
# 2c. passage_number: integer
# 2d. passage_text: text
# 2e. section_type: text
# 2f. type: text
# 2g. offset: integer
# 2h. relations: text

# 3. entities: contains the entities for each passage
# 3a. entity_id: primary key # this is the identifier for the entity, e.g. MESH:D030342
# 3b. type: text # this is the type of entity, e.g. Disease
# 3c. database: text # this is the database, e.g. ncbi_mesh
# 3d. normalized_id: text # this is the normalized id, e.g. D030342
# 3e. biotype: text # this is the type, e.g. disease
# 3f. name: text # this is the name of the entity, e.g. Genetic Diseases Inborn
# 3g. accession: text # this is the pubtator accession, e.g. @DISEASE_Genetic_Diseases_Inborn

# 4. annotations: contains the annotations for each entity
# 4a. annotation_id: primary key # this is the identifier for the annotation
# 4b. entity_id: foreign key # this is the identifier for the entity, e.g. MESH:D030342
# 4c. accession: text # this is the pubtator accession, e.g. @DISEASE_Genetic_Diseases_Inborn
# 4d. offset_start: integer # this is the start position of the annotation in the document
# 4e. length: integer # this is the length of the annotation text
# 4f. text: text # this is the annotation text
# 4g. pubmed_id: text # this is the pubmed id
# 4h. passage_id: foreign key # this is the identifier for the passage
# 
"""
