"""Rebuilds SQLite3 databases which are too large to distribute"""

# --- Third Party Imports ---
import sqlite3
import pandas as pd
import os

# --- Local Imports ---
from app.utils import resource_path
from app.database.database_creation import add_indexes_to_all_tables


def rebuild_db_files() -> None:
    """Rebuilds SQLite3 databases which are too large to distribute"""

    print("Rebuild of database files started ...")
    folder_path = "assets/external_data"
    # These paths point to the CSV halves
    pubtator_count_path_first = resource_path(
        f"{folder_path}/pubtator_count_first_half.csv")
    pubtator_count_path_second = resource_path(
        f"{folder_path}/pubtator_count_second_half.csv")

    # Target database paths and table/column names
    pubtator_count_target_db_path = resource_path(
        f"{folder_path}/pubtator_count.db")
    pubtator_count_db_table_name = "IdentifierCounts"
    first_col_name = "Identifier"
    second_col_name = "Count"

    # Check if db exists and is not empty
    if os.path.exists(pubtator_count_target_db_path) and os.path.getsize(pubtator_count_target_db_path) > 0:
        print(
            f"Database file {pubtator_count_target_db_path} already exists and is not empty. Skipping rebuild.")
    else:
        print(f"Starting rebuild for pubtator_count.db")
        # Write a new sqlite3 database from the two CSV halves, with table and column names, combining both halves
        conn = sqlite3.connect(pubtator_count_target_db_path)
        cursor = conn.cursor()
        cursor.execute(
            f"CREATE TABLE IF NOT EXISTS {pubtator_count_db_table_name} ({first_col_name} TEXT, {second_col_name} INTEGER);")

        for csv_path in [pubtator_count_path_first, pubtator_count_path_second]:
            df = pd.read_csv(csv_path)
            df.to_sql(pubtator_count_db_table_name, conn,
                      if_exists='append', index=False)

        conn.commit()
        conn.close()
    print(f"Finished rebuild (1/3)")

    # Repeat similar process for pubtator_doc_count
    pubtator_doc_count_path_first = resource_path(
        f"{folder_path}/pubtator_doc_count_first_half.csv")
    pubtator_doc_count_path_second = resource_path(
        f"{folder_path}/pubtator_doc_count_second_half.csv")
    pubtator_doc_count_target_db_path = resource_path(
        f"{folder_path}/pubtator_doc_count.db")
    pubtator_doc_count_db_table_name = "IDCounts"
    first_col_name = "ID"
    second_col_name = "Count"

    # check if db exists and is not empty
    if os.path.exists(pubtator_doc_count_target_db_path) and os.path.getsize(pubtator_doc_count_target_db_path) > 0:
        print(
            f"Database file {pubtator_doc_count_target_db_path} already exists and is not empty. Skipping rebuild.")
    else:
        print(f"Starting rebuild for pubtator_doc_count.db")
        # Write a new sqlite3 database from the two CSV halves, with table and column names, combining both halves
        conn = sqlite3.connect(pubtator_doc_count_target_db_path)
        cursor = conn.cursor()
        cursor.execute(
            f"CREATE TABLE IF NOT EXISTS {pubtator_doc_count_db_table_name} ({first_col_name} TEXT, {second_col_name} INTEGER);")

        for csv_path in [pubtator_doc_count_path_first, pubtator_doc_count_path_second]:
            df = pd.read_csv(csv_path)
            df.to_sql(pubtator_doc_count_db_table_name,
                      conn, if_exists='append', index=False)

        conn.commit()
        conn.close()
    print(f"Finished rebuild (2/3)")

    # Finally, rebuild gene_summary database from its CSV
    gene_summary_path = resource_path(
        f"{folder_path}/gene2organism_mapping/gene_summary.csv")
    gene_summary_target_db_path = resource_path(
        f"{folder_path}/gene2organism_mapping/gene_summary.db")
    gene_summary_db_table_name = "gene_summary"
    col_names = ["tax_id", "gene_id", "source"]

    # check if db exists and is not empty
    if os.path.exists(gene_summary_target_db_path) and os.path.getsize(gene_summary_target_db_path) > 0:
        print(
            f"Database file {gene_summary_target_db_path} already exists and is not empty. Skipping rebuild.")
    else:
        print(f"Starting rebuild for gene_summary.db")
        # Write a new sqlite3 database from the CSV, with table and column names
        conn = sqlite3.connect(gene_summary_target_db_path)
        cursor = conn.cursor()
        cursor.execute(
            f"CREATE TABLE IF NOT EXISTS {gene_summary_db_table_name} ({', '.join([col + ' TEXT' for col in col_names])});")

        df = pd.read_csv(gene_summary_path)
        df.to_sql(gene_summary_db_table_name, conn,
                  if_exists='append', index=False)

        conn.commit()
        conn.close()
    print(f"Finished rebuild (3/3)")

    # Finally, add indexes to all tables in the rebuilt databases
    print("Adding indexes to all rebuilt database tables...")
    add_indexes_to_all_tables(pubtator_count_target_db_path)
    add_indexes_to_all_tables(pubtator_doc_count_target_db_path)
    add_indexes_to_all_tables(gene_summary_target_db_path)
    print("Indexes added successfully.")
    print("Rebuild of database files completed.")
