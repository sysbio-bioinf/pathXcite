"""Provides functions to validate the schema and data integrity of PubMed databases"""

# --- Standard Library Imports ---
import os
import sqlite3

# --- Local Imports ---
from app.database.database_query import get_article_count


# --- Public Functions ---
def scan_and_validate_databases(folder_path: str) -> dict[str, dict]:
    """
    Recursively scans a folder for .db files, validates each one using validate_database(),
    and returns a dictionary with validation status and article count.

    Args:
        folder_path (str): Path to the folder to scan.

    Returns:
        dict: A dictionary where keys are database file paths and values are dictionaries with
              'is_valid' (bool), 'numberArticles' (int), and 'issues' (list of str).
    """
    results: dict[str, dict] = {}

    # Walk through the folder and subfolders
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith(".db"):
                db_path = os.path.join(root, file)

                # Validate using the existing function
                validation_results: dict = _validate_database(db_path)
                is_valid: bool = validation_results.get('is_valid', False)
                # Get number of entries in 'articles' table
                article_count: int = get_article_count(
                    db_path) if is_valid else 0

                # Store the results
                results[db_path] = {
                    'is_valid': is_valid,
                    'numberArticles': article_count,
                    'issues': validation_results.get('issues', [])
                }

    return results

# --- Private Functions ---


def _validate_database(db_path: str) -> dict:
    """
    Validate the database schema and data integrity.

    Args:
        db_path (str): Path to the SQLite database file.

    Returns:
        dict: A dictionary with validation results, including 'is_valid' (bool) and
        'issues' (list of str).
    """
    expected_tables = {
        "articles": {
            "pubmed_id": "TEXT PRIMARY KEY",
            "pmc_id": "TEXT",
            "title": "TEXT",
            "authors": "TEXT",
            "journal": "TEXT",
            "year": "INTEGER",
            "keywords": "TEXT",
            "doi": "TEXT",
            "mesh_terms": "TEXT",
            "chemical_list": "TEXT",
            "abstract": "TEXT",
            "publication_type": "TEXT",
            "language": "TEXT",
            "country": "TEXT",
            "institution": "TEXT",
            "funding": "TEXT"
        },
        "passages": {
            "passage_id": "INTEGER PRIMARY KEY",
            "pubmed_id": "TEXT",
            "pmc_id": "TEXT",
            "passage_number": "INTEGER",
            "passage_text": "TEXT",
            "section_type": "TEXT",
            "type": "TEXT",
            "offset": "INTEGER",
            "relations": "TEXT"
        },
        "entities": {
            "entity_id": "TEXT PRIMARY KEY",
            "type": "TEXT",
            "database": "TEXT",
            "normalized_id": "TEXT",
            "biotype": "TEXT",
            "name": "TEXT",
            "accession": "TEXT"
        },
        "annotations": {
            "annotation_id": "INTEGER PRIMARY KEY",
            "entity_id": "TEXT",
            "accession": "TEXT",
            "offset_start": "INTEGER",
            "length": "INTEGER",
            "text": "TEXT",
            "pubmed_id": "TEXT",
            "passage_number": "INTEGER"
        }
    }

    issues: list[str] = []
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if all expected tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = {row[0] for row in cursor.fetchall()}

        missing_tables = set(expected_tables.keys()) - tables
        if missing_tables:
            tmp_issue = f"Missing tables: {missing_tables}"
            issues.append(tmp_issue)

        # Check columns for each table
        for table, expected_columns in expected_tables.items():
            cursor.execute(f"PRAGMA table_info({table});")
            actual_columns = {row[1]: row[2].upper()
                              for row in cursor.fetchall()}

            for column, col_type in expected_columns.items():
                if column not in actual_columns:
                    tmp_issue = f"Missing column '{column}' in table '{table}'"
                    issues.append(tmp_issue)
                else:
                    # Check only the type part
                    if actual_columns[column] != col_type.split()[0]:
                        tmp_issue = f"Column '{column}' in table '{table}' has incorrect type: {actual_columns[column]}, expected {col_type}"
                        issues.append(tmp_issue)

        # Check for invalid entries (basic validity check)
        for table in expected_tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table};")
            # count = cursor.fetchone()[0]

    except sqlite3.Error as e:
        tmp_issue = f"Database error: {e}"
        issues.append(tmp_issue)
    finally:
        conn.close()

    return {'is_valid': not bool(issues), 'issues': issues}
