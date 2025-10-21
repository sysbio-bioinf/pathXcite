"""Provides functions to create the local database schema for PubMed data"""

# --- Standard Library Imports ---
from contextlib import closing, contextmanager
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


def add_indexes_to_all_tables(
    db_path: str,
    *,
    dry_run: bool = False,
    include_unique_columns: bool = True,
    verbose: bool = True
) -> None:
    """
    Add helpful indexes to every user table in a SQLite database.
    (Speeds up especially the document card selection)

    What it does:
      - For each user table (not a view, not sqlite_*), create an index for:
          (1) each non-PK column that doesn't already have a single-column index
          (2) each foreign key column (if not already indexed)
      - Index names follow: idx_<table>__<col>  (double underscore between table and column)
      - Uses IF NOT EXISTS to be idempotent and avoid failure if a same-named index already exists.

    Parameters
    ----------
    db_path : str
        Path to the SQLite database file.
    dry_run : bool, default False
        If True, prints the CREATE INDEX statements but does not execute them.
    include_unique_columns : bool, default True
        If False, columns that are the sole target of a UNIQUE constraint are not
        additionally single-indexed (they're already backed by an index).
    verbose : bool, default True
        If True, prints progress.
    """

    def quote_ident(name: str) -> str:
        # Minimal identifier quoting for SQLite identifiers
        return '"' + name.replace('"', '""') + '"'

    @contextmanager
    def connect(db_path):
        con = sqlite3.connect(db_path)
        try:
            con.execute("PRAGMA foreign_keys = ON;")
            yield con
        finally:
            con.close()

    with connect(db_path) as con, closing(con.cursor()) as cur:
        # Get all user tables (skip views and sqlite_internal tables)
        cur.execute("""
            SELECT name, type
            FROM sqlite_master
            WHERE type IN ('table','view')
              AND name NOT LIKE 'sqlite_%'
        """)
        objects = cur.fetchall()

        tables = [name for (name, typ) in objects if typ == 'table']
        views = [name for (name, typ) in objects if typ == 'view']

        if verbose and views:
            print(f"Skipping views (not indexable): {', '.join(views)}")

        # Collect planned statements
        create_statements = []

        for table in tables:
            # Skip if it's a WITHOUT ROWID table? (still indexable)
            if verbose:
                print(f"\nAnalyzing table: {table}")

            # Columns and PK info
            cur.execute(f"PRAGMA table_info({quote_ident(table)});")
            cols_info = cur.fetchall()
            # PRAGMA table_info returns: cid, name, type, notnull, dflt_value, pk
            col_names = [row[1] for row in cols_info]
            pk_cols = {row[1] for row in cols_info if row[5] > 0}

            # Existing indexes and their columns
            cur.execute(f"PRAGMA index_list({quote_ident(table)});")
            idx_list = cur.fetchall()
            # PRAGMA index_list returns: seq, name, unique, origin, partial
            existing_indexes = []
            for _, idx_name, is_unique, *_ in idx_list:
                cur.execute(f"PRAGMA index_info({quote_ident(idx_name)});")
                idx_cols = [r[2] for r in cur.fetchall()]  # seqno, cid, name
                existing_indexes.append(
                    (idx_name, bool(is_unique), tuple(idx_cols)))

            # Build helpers
            single_col_indexed = {cols[0] for _, _,
                                  cols in existing_indexes if len(cols) == 1}
            unique_single_col = {cols[0] for _, is_unique, cols in existing_indexes
                                 if is_unique and len(cols) == 1}

            # Foreign keys
            cur.execute(f"PRAGMA foreign_key_list({quote_ident(table)});")
            fk_rows = cur.fetchall()
            # PRAGMA foreign_key_list returns:
            # (id, seq, table, from, to, on_update, on_delete, match)
            fk_cols = {r[3] for r in fk_rows if r[3] is not None}

            # Decide which columns should get a single-column index
            candidate_cols = []
            for c in col_names:
                if c in pk_cols:
                    continue  # primary keys already indexed
                if not include_unique_columns and c in unique_single_col:
                    continue  # already uniquely indexed
                if c in single_col_indexed:
                    continue  # already has a single-col index
                candidate_cols.append(c)

            # Prioritize foreign-key columns (put them first)
            fk_candidates = [c for c in candidate_cols if c in fk_cols]
            non_fk_candidates = [c for c in candidate_cols if c not in fk_cols]

            # Prepare CREATE INDEX statements (IF NOT EXISTS for safety)
            for c in fk_candidates + non_fk_candidates:
                idx_name = f"idx_{table}__{c}"
                stmt = f"CREATE INDEX IF NOT EXISTS {quote_ident(idx_name)} ON {quote_ident(table)} ({quote_ident(c)});"
                create_statements.append(stmt)

            # Also ensure foreign key columns have an index even if excluded above
            for c in fk_cols:
                if c in pk_cols:
                    continue
                if c not in single_col_indexed:
                    idx_name = f"idx_{table}__{c}"
                    stmt = f"CREATE INDEX IF NOT EXISTS {quote_ident(idx_name)} ON {quote_ident(table)} ({quote_ident(c)});"
                    if stmt not in create_statements:
                        create_statements.append(stmt)

        # Execute or print
        if not create_statements:
            if verbose:
                print("\nNo new indexes to create.")
            return

        if dry_run:
            if verbose:
                print("\n-- Dry run: planned CREATE INDEX statements --")
            for s in create_statements:
                print(s)
            return

        if verbose:
            print("\nCreating indexes in a single transaction...")

        with con:  # transaction
            for s in create_statements:
                con.execute(s)

        if verbose:
            print(f"Done. Created/ensured {len(create_statements)} indexes.")


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
