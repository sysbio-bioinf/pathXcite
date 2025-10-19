"""Utility functions for setting up the application environment"""

# --- Standard Library Imports ---
import os
import sqlite3


# --- Public Functions ---
def map_gene_ids_to_taxids(db_folder: str, gene_ids: list) -> dict:
    """
    Efficiently maps a list of gene IDs to their respective tax IDs using an 
    indexed SQLite database.

    Args:
        db_folder (str): The directory where the SQLite database is located.
        gene_ids (list): A list of gene IDs (as strings or integers).

    Returns:
        dict: A mapping of gene IDs to tax IDs.
    """

    db_path = os.path.join(db_folder, "gene_summary.db")
    if not os.path.exists(db_path):
        raise FileNotFoundError(
            f"Database not found at {db_path}. Run create_gene_db.py first.")

    # Convert gene IDs to integers, ignoring invalid ones
    valid_gene_ids = set()
    for gene_id in gene_ids:
        try:
            if gene_id is not None:
                # Convert string numbers to int
                valid_gene_ids.add(int(gene_id))
        except ValueError:
            pass  # Skip invalid values

    # If there are no valid gene IDs, return an empty dictionary
    if not valid_gene_ids:
        return {}

    # Connect to SQLite
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Batch querying for efficiency
    taxid_mapping: dict = {}
    batch_size = 1000
    valid_gene_ids = list(valid_gene_ids)  # Convert set back to list

    for i in range(0, len(valid_gene_ids), batch_size):
        batch = valid_gene_ids[i:i+batch_size]
        query = f"""SELECT gene_id, tax_id
        FROM gene_summary 
        WHERE gene_id IN ({','.join(['?'] * len(batch))})
        """
        cursor.execute(query, batch)

        for gene_id, tax_id in cursor.fetchall():
            taxid_mapping[gene_id] = tax_id

    conn.close()
    return taxid_mapping
