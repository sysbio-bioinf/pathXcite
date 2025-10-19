"""Manages interactions with the local PubMed database"""

# --- Standard Library Imports ---
import sqlite3

# --- Third Party Imports ---
import pandas as pd

# --- Public Classes ---


class DatabaseManager:
    """Class to manage interactions with the local PubMed database."""

    def __init__(self, db_path: str):
        """
        Initialize the DatabaseManager with the path to the database.

        Args:
            db_path (str): Path to the SQLite database file.
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)

    def fetch_data(self, query: str) -> pd.DataFrame:
        """
        Fetch data from the database using the provided SQL query.

        Args:
            query (str): SQL query to execute.

        Returns:
            pd.DataFrame: DataFrame containing the query results.

        """
        df: pd.DataFrame = pd.read_sql_query(query, self.conn)
        return df

    def get_number_articles(self) -> int:
        """
        Get the total number of articles in the database.

        Returns:
            int: Total number of articles.
        """
        c = self.conn.cursor()
        c.execute("SELECT COUNT(*) FROM articles")
        result: tuple = c.fetchone()
        return result[0] if result else 0

    def get_pubmed_id_by_pmc_id(self, pmc_id: str) -> str | None:
        """
        Get the PubMed ID corresponding to a given PMC ID.

        Args:
            pmc_id (str): The PMC ID to look up.

        Returns:
            str | None: The corresponding PubMed ID, or None if not found.
        """
        c = self.conn.cursor()
        c.execute("SELECT pubmed_id FROM articles WHERE pmc_id = ?", (pmc_id,))
        result: tuple | None = c.fetchone()
        return result[0] if result else None

    '''def count_passages_per_pmc_id(self, pmc_id: str) -> int:
        """
        Count the number of passages for a given PMC ID.

        Args:
            pmc_id (str): The PMC ID to count passages for.

        Returns:
            int: The number of passages for the given PMC ID.
        """
        c = self.conn.cursor()
        c.execute("SELECT COUNT(*) FROM passages WHERE pmc_id = ?", (pmc_id,))
        result: tuple | None = c.fetchone()
        return result[0] if result else 0'''

    def get_passage_data_by_pmc_and_pubmed(self, pmc_id: str, pubmed_id: str) -> dict:
        """
        Get passage data and annotations for a given PMC ID and PubMed ID.

        Args:
            pmc_id (str): The PMC ID to look up.
            pubmed_id (str): The PubMed ID to look up.

        Returns:
            dict: A dictionary containing passage data and annotations.
        """
        c = self.conn.cursor()

        # Step 1: Get all passage numbers for the given pmc_id
        c.execute("SELECT passage_number FROM passages WHERE pmc_id = ?", (pmc_id,))
        passages: list[tuple] = c.fetchall()
        passage_numbers: list[int] = [row[0] for row in passages]

        annotations: dict[int, list[tuple]] = {}
        passage_types: dict[int, str] = {}
        if not passage_numbers:
            # No passages found for this PMC ID
            return {'annotations': annotations, 'passage_types': passage_types}

        # Step 2: Get all annotations for the given pubmed_id and passage_number
        for passage_number in passage_numbers:
            c.execute(
                "SELECT * FROM annotations WHERE pubmed_id = ? AND passage_number = ?",
                (pubmed_id, passage_number),
            )
            annotations[passage_number] = c.fetchall()
            c.execute(
                "SELECT section_type FROM passages WHERE pmc_id = ? AND passage_number = ?",
                (pmc_id, passage_number),
            )
            passage_types[passage_number] = c.fetchone()[0]

        # Returns a list of annotation tuples
        return {'annotations': annotations, 'passage_types': passage_types}

    def get_passage_data_by_pmc_and_pubmed_only_gene(self, pmc_id: str, pubmed_id: str) -> dict:
        """
        Get passage data and gene annotations for a given PMC ID and PubMed ID.

        Args:
            pmc_id (str): The PMC ID to look up.
            pubmed_id (str): The PubMed ID to look up.

        Returns:
            dict: A dictionary containing passage data and annotations.
        """
        c = self.conn.cursor()

        # Step 1: Get all passage numbers for the given pmc_id
        c.execute("SELECT passage_number FROM passages WHERE pmc_id = ?", (pmc_id,))
        passages: list[tuple] = c.fetchall()
        passage_numbers: list[int] = [row[0] for row in passages]

        annotations: dict[int, list[tuple]] = {}
        passage_types: dict[int, str] = {}
        if not passage_numbers:
            # No passages found for this PMC ID
            return {'annotations': annotations, 'passage_types': passage_types}

        # Step 2: Get all annotations for the given pubmed_id and passage_number
        for passage_number in passage_numbers:
            c.execute(
                """SELECT * FROM annotations 
                    WHERE pubmed_id = ? 
                    AND passage_number = ? 
                    AND accession 
                    LIKE '%@GENE%'""",
                (pubmed_id, passage_number),
            )
            annotations[passage_number] = c.fetchall()
            c.execute(
                """SELECT section_type 
                FROM passages 
                WHERE pmc_id = ? 
                AND passage_number = ?""",
                (pmc_id, passage_number),
            )
            passage_types[passage_number] = c.fetchone()[0]

         # Returns a list of annotation tuples
        return {'annotations': annotations, 'passage_types': passage_types}
