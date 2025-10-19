"""Provides functions to update PubMed data in the local database"""

# --- Standard Library Imports ---
import json
import sqlite3
from typing import Any

# --- Local Imports ---
from app.api_utils.article_retrieval import get_metadata_and_pubtator_data
from app.api_utils.pmc_pmid_utils import fetch_pmids

# --- Public Functions ---


def add_articles_to_db(main_app: Any, pubmed_or_pmc_id: list,
                       db_path: str, email: str = None, api_key: str = None) -> None:
    """
    Adds articles to the database.

    Args:
        main_app (Any): The main application instance.
        pubmed_or_pmc_id (list): List of PubMed or PMC IDs.
        db_path (str): Path to the SQLite database.
        email (str, optional): Email address for API access.
        api_key (str, optional): API key for authentication.

    Returns:
        None
    """

    pubmed_ids: list[str] = []
    pmc_ids: list[str] = []
    for tmp_id in pubmed_or_pmc_id:
        id_potential_pmid = tmp_id.lower().replace(
            "pmid ", "").replace("pmid:", "").replace("pmid", "")
        was_added = False
        if len(str(id_potential_pmid)) <= 8 and str(id_potential_pmid).isdigit():
            pubmed_ids.append(str(tmp_id))
            was_added = True
        if tmp_id.lower().startswith("pmc"):
            id_potential_pmc = tmp_id.lower().replace(
                "pmc ", "pmc").replace("pmc: ", "pmc")
            id_potential_pmc = id_potential_pmc.replace(
                "pmc:", "pmc").replace("pmc", "PMC")
            if len(str(id_potential_pmc)) <= 12 and str(id_potential_pmc[3:]).isdigit():
                pmc_ids.append(str(id_potential_pmc))
                was_added = True
        elif tmp_id.startswith("PMC") and len(str(tmp_id)) <= 12:
            pmc_ids.append(tmp_id)
            was_added = True

        if not was_added:
            print(
                f"We skipped the id {tmp_id} because it is not a valid pmc or pm id.")

    pmc_to_pubmed_id_results: dict[str, str] = fetch_pmids(main_app, pmc_ids,
                                                           email=email, api_key=api_key)

    pubmed_ids.extend(pmc_to_pubmed_id_results.values())

    # make sure all ids are unique and do not contain any prefixes
    pubmed_ids = list(set([str(id).replace("PMID:", "").replace(
        "PMID ", "").replace("PMID", "") for id in pubmed_ids]))

    results: dict[str, Any] = get_metadata_and_pubtator_data(main_app=main_app,
                                                             pubmed_ids=pubmed_ids, email=email,
                                                             api_key=api_key)

    _store_pubtator_data(results, db_path)

# --- Private Functions ---


def _store_pubtator_data(data: dict[str, Any], db_path: str) -> None:
    """
    Stores retrieved Pubtator data into the database.

    Args:
        data (dict): Retrieved metadata and Pubtator content.
        db_path (str): Path to the SQLite database.

    Returns:
        None
    """

    articles: list[dict[str, Any]] = []
    passages: list[dict[str, Any]] = []
    entities: list[dict[str, Any]] = []
    annotations: list[dict[str, Any]] = []
    for pubmed_id, retrieved_metadata_and_pubtator_content in data.items():
        pubmed_id = str(pubmed_id)
        article_content: dict[str, Any] = retrieved_metadata_and_pubtator_content.get(
            'metadata', {})
        if article_content is not None:
            pmc_id = str(article_content.get('pmc_id', None))
            article: dict[str, Any] = {}
            # Convert lists and dictionary values to strings
            article['pubmed_id'] = pubmed_id
            article['pmc_id'] = pmc_id
            article['title'] = article_content.get('title', None)
            article['journal'] = article_content.get('journal', None)
            article['year'] = article_content.get('year', None)
            article['doi'] = article_content.get('doi', None)
            article['abstract'] = article_content.get('abstract', None)
            article['language'] = article_content.get('language', None)
            article['country'] = article_content.get('country', None)
            article['institution'] = article_content.get('institution', None)
            article['authors'] = json.dumps(article_content.get('authors', []))
            article['keywords'] = json.dumps(
                article_content.get('keywords', []))
            article['mesh_terms'] = json.dumps(
                article_content.get('mesh_terms', []))
            article['chemical_list'] = json.dumps(
                article_content.get('chemical_list', []))
            article['publication_type'] = json.dumps(
                article_content.get('publication_type', []))
            article['funding'] = json.dumps(article_content.get('funding', []))
            articles.append(article)
            pubtator_content = retrieved_metadata_and_pubtator_content.get(
                'pubtator_content', {})

            if pubtator_content:
                for passage_number, passage in enumerate(pubtator_content.get('passages', [])):
                    passages.append({
                        'pubmed_id': pubmed_id,
                        'pmc_id': pmc_id,
                        'passage_number': passage_number,
                        'passage_text': passage.get('text', None),
                        'section_type': passage.get('infons', {}).get('section_type', None),
                        'type': passage.get('infons', {}).get('type', None),
                        'offset': passage.get('offset', None),
                        'relations': json.dumps(passage.get('infons', {}).get('relations', {}))
                    })

                    for entity in passage.get('annotations', []):
                        entity_id = entity.get(
                            'infons', {}).get('identifier', None)
                        entities.append({
                            'entity_id': entity_id,
                            'type': entity.get('infons', {}).get('type', None),
                            'database': entity.get('infons', {}).get('ncbi_taxonomy', None),
                            'normalized_id': entity.get('infons', {}).get('normalized_id', None),
                            'biotype': entity.get('infons', {}).get('biotype', None),
                            'name': entity.get('infons', {}).get('name', None),
                            'accession': entity.get('infons', {}).get('accession', None)
                        })

                        annotations.append({
                            'entity_id': entity_id,
                            'accession': entity.get('infons', {}).get('accession', None),
                            'offset_start': entity.get('locations', [{}])[0].get('offset', None),
                            'length': entity.get('locations', [{}])[0].get('length', None),
                            'text': entity.get('text', None),
                            'pubmed_id': pubmed_id,
                            'passage_number': passage_number
                        })

    _add_articles(articles, db_path)
    _add_passages(passages, db_path)
    _add_entities(entities, db_path)
    _add_annotations(annotations, db_path)


def _add_articles(articles: list, db_path: str) -> None:
    """
    Adds a list of articles to the database.
    If an article (identified by its pubmed id) already exists in the database, 
    it is checked whether the data is the same.
    If the data is different, the existing data is updated but only with new information 
    (meaning only the columns that have not been filled yet).
    If the data is the same, the article is skipped.

    Args:
        articles (list): List of article dictionaries to add.
        db_path (str): Path to the SQLite database.

    Returns:
        None
    """
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    for article in articles:
        # check if article with pubmed id already exists in database
        c.execute('''SELECT * FROM articles WHERE pubmed_id=?''',
                  (article['pubmed_id'],))
        existing_article: tuple | None = c.fetchone()
        if existing_article is None:
            c.execute(
                """
                    INSERT INTO articles (
                        pubmed_id, pmc_id, title, authors, journal, year, keywords, doi,
                        mesh_terms, chemical_list, abstract, publication_type, language,
                        country, institution, funding
                    )
                    VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?, ?
                    )
                    """,
                (
                    article["pubmed_id"],
                    article["pmc_id"],
                    article["title"],
                    article["authors"],
                    article["journal"],
                    article["year"],
                    article["keywords"],
                    article["doi"],
                    article["mesh_terms"],
                    article["chemical_list"],
                    article["abstract"],
                    article["publication_type"],
                    article["language"],
                    article["country"],
                    article["institution"],
                    article["funding"],
                ),
            )

        else:
            if existing_article is not None and c.description:
                existing_article = dict(zip([description[0] for description in c.description],
                                            existing_article))
            else:
                existing_article: dict = {}
            for key in article:
                if key in existing_article and existing_article[key] is None:
                    c.execute(f'''UPDATE articles SET {key}=? WHERE pubmed_id=?''',
                              (article[key], article['pubmed_id']))
    conn.commit()
    conn.close()


def _add_passages(passages: list, db_path: str) -> None:
    """
    Adds a list of passages to the database.
    If a passage (identified by its pubmed id and passage number) already exists
    in the database, it is checked whether the data is the same.
    If the data is different, the existing data is updated but only with
    new information (meaning only the columns that have not been filled yet).
    If the data is the same, the passage is skipped.

    Args:
        passages (list): List of passage dictionaries to add.
        db_path (str): Path to the SQLite database.

    Returns:
        None
    """

    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    for passage in passages:
        c.execute('''SELECT * FROM passages WHERE pubmed_id=? AND passage_number=?''',
                  (passage['pubmed_id'], passage['passage_number']))
        if c.fetchone() is None:
            c.execute("""INSERT INTO passages (
                        pubmed_id, pmc_id, passage_number, passage_text, section_type, 
                        type, offset, relations
                        ) 
                        VALUES (
                        ?,?,?,?,?,?,?,?
                        )
                      """,
                      (passage['pubmed_id'], passage['pmc_id'], passage['passage_number'],
                       passage['passage_text'], passage['section_type'], passage['type'],
                       passage['offset'], passage['relations']))
        else:
            existing_passage = c.fetchone()
            if existing_passage is not None and c.description:
                existing_passage = dict(zip([description[0] for description in c.description],
                                            existing_passage))
            else:
                existing_passage: dict = {}

            for key in passage:
                if key in existing_passage and existing_passage[key] is None:
                    c.execute(f"""UPDATE passages SET {key}=?
                              WHERE pmc_id=? AND passage_number=?""",
                              (passage[key], passage['pmc_id'], passage['passage_number']))
    conn.commit()
    conn.close()


def _add_entities(entities: list, db_path: str) -> None:
    """ 
    Adds a list of entities to the database.
    If an entity (identified by its entity_id) already exists in the database,
    it is checked whether the data is the same.
    If the data is different, the existing data is updated but only with new information
    (meaning only the columns that have not been filled yet).
    If the data is the same, the entity is skipped.

    Args:
        entities (list): List of entity dictionaries to add.
        db_path (str): Path to the SQLite database.

    Returns:
        None
    """
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    for entity in entities:
        c.execute("""SELECT * FROM entities WHERE entity_id=?""",
                  (entity['entity_id'],))
        if c.fetchone() is None:
            c.execute("""INSERT INTO entities (
                      entity_id, type, database, normalized_id, biotype, 
                      name, accession
                      ) VALUES (
                      ?,?,?,?,?,?,?
                      )""",
                      (entity['entity_id'], entity['type'], entity['database'],
                       entity['normalized_id'], entity['biotype'], entity['name'],
                       entity['accession']
                       )
                      )
        else:
            c.execute("""SELECT * FROM entities WHERE entity_id=?""",
                      (entity['entity_id'],))
            existing_entity = c.fetchone()
            existing_entity = dict(zip([description[0] for description in c.description],
                                       existing_entity))
            for key in entity:
                if existing_entity[key] is None:
                    c.execute(f"""UPDATE entities SET {key}=? WHERE entity_id=?""",
                              (entity[key], entity['entity_id']))
    conn.commit()
    conn.close()


def _add_annotations(annotations: list, db_path: str) -> None:
    """ 
    Adds a list of annotations to the database.
    If an annotation (identified by its pubmed_id and offset_start) already
    exists in the database, it is checked whether the data is the same.
    If the data is different, the existing data is updated but only with
    new information (meaning only the columns that have not been filled yet
    If the data is the same, the annotation is skipped.

    Args:
        annotations (list): List of annotation dictionaries to add.
        db_path (str): Path to the SQLite database.

    Returns:
        None
    """
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    for annotation in annotations:
        c.execute("""SELECT * FROM annotations WHERE pubmed_id=? AND offset_start=?""",
                  (annotation['pubmed_id'], annotation['offset_start']))
        existing_annotation = c.fetchone()  # Store the result

        if existing_annotation is None:
            c.execute("""INSERT INTO annotations (
                      entity_id, accession, offset_start,
                      length, text, pubmed_id, passage_number
                      )
                         VALUES (
                      ?,?,?,?,?,?,?
                      )""",
                      (annotation['entity_id'], annotation['accession'], annotation['offset_start'],
                       annotation['length'], annotation['text'], annotation['pubmed_id'],
                       annotation['passage_number']))
        else:
            # Convert tuple to dictionary
            existing_annotation_dict = dict(zip([description[0] for description in c.description],
                                                existing_annotation))

            for key in annotation:
                if existing_annotation_dict.get(key) is None:
                    c.execute(f"""UPDATE annotations SET {key}=?
                              WHERE pubmed_id=? AND offset_start=?""",
                              (annotation[key], annotation['pubmed_id'],
                               annotation['offset_start']))

    conn.commit()
    conn.close()
