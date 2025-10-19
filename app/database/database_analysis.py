"""Provides functions to analyze PubMed data from the local database"""

# --- Standard Library Imports ---
from collections import Counter, defaultdict

# --- Public Functions ---


def analyze_pubmed_data(data: list[dict], pubmed_ids: set[str]) -> dict:
    """
    Analyze PubMed data for given PubMed IDs.

    Args:
        data: List of article metadata dictionaries.
        pubmed_ids: Set of PubMed IDs to analyze.

    Returns:
        dict: Analysis results including frequencies and distributions.
    """
    # Normalize pubmed_ids to strings and remove None values
    pubmed_ids = set(str(p) for p in pubmed_ids if p is not None)

    results = {
        "selected_pubmed_ids": list(pubmed_ids),
        "num_docs_with_keywords": 0,
        "keyword_frequencies": Counter(),
        "num_docs_with_meshterms": 0,
        "mesh_term_frequencies": Counter(),
        "entity_document_frequencies": Counter(),
        "entity_annotation_frequencies": Counter(),
        "journal_frequencies": Counter(),
        "publication_years": Counter(),         # year -> count
        "publication_doc_lists": defaultdict(list),  # year -> [pmid]
        # year -> [{"pmid","title"}]
        "publications_by_year": defaultdict(list),
        "num_docs_with_pmc_id": 0,
        "passage_distribution": Counter(),
    }

    for article in data:
        pmid = str(article.get("pubmed_id", "")).strip()
        if not pmid or pmid not in pubmed_ids:
            continue

        # Normalize fields
        journal = (article.get("journal") or "").strip() or "Unknown Journal"
        title = (article.get("title") or "").strip()
        # year as int if possible
        year_raw = article.get("year")
        try:
            year = int(year_raw)
        except (TypeError, ValueError):
            # skip items without a usable year
            continue

        # Count journals
        results["journal_frequencies"][journal] += 1

        # Count publication years & store doc lists
        results["publication_years"][year] += 1
        results["publication_doc_lists"][year].append(pmid)

        # Store full entries for modal (pmid + title)
        results["publications_by_year"][year].append({
            "pmid": pmid,
            "title": title,
        })

        # Count PMC IDs
        if article.get("pmc_id"):
            results["num_docs_with_pmc_id"] += 1

        # Count keywords
        kws = article.get("keywords") or []
        if kws:
            results["num_docs_with_keywords"] += 1
            results["keyword_frequencies"].update(kws)

        # Count MeSH terms
        mesh = article.get("mesh_terms") or []
        if mesh:
            results["num_docs_with_meshterms"] += 1
            results["mesh_term_frequencies"].update(mesh)

        # Entities & annotations
        ann = article.get("annotations") or {}
        for _, entity_data in ann.items():
            gene = (entity_data.get("gene_symbol") or "").strip()
            if not gene:
                continue
            results["entity_document_frequencies"][gene] += 1
            for a in (entity_data.get("annotations") or []):
                results["entity_annotation_frequencies"][gene] += 1
                passage_no = a.get("passage_number")
                if passage_no is not None:
                    results["passage_distribution"][passage_no] += 1

    # ---- Post-process / normalize structures for JSON friendliness ----
    # Deduplicate per-year pmids and per-year (pmid,title) pairs while preserving order
    for y, pmids in results["publication_doc_lists"].items():
        seen: set[str] = set()
        dedup_pmids: list[str] = []
        for p in pmids:
            if p not in seen:
                seen.add(p)
                dedup_pmids.append(p)
        results["publication_doc_lists"][y] = dedup_pmids

    for y, entries in results["publications_by_year"].items():
        seen: set[tuple[str, str]] = set()
        dedup_entries: list[dict] = []
        for e in entries:
            key = e.get("pmid", ""), e.get("title", "")
            if key not in seen:
                seen.add(key)
                dedup_entries.append(e)
        results["publications_by_year"][y] = dedup_entries

    # Convert Counters/defaultdicts to plain dicts
    results["keyword_frequencies"] = dict(results["keyword_frequencies"])
    results["mesh_term_frequencies"] = dict(results["mesh_term_frequencies"])
    results["entity_document_frequencies"] = dict(
        results["entity_document_frequencies"])
    results["entity_annotation_frequencies"] = dict(
        results["entity_annotation_frequencies"])
    results["journal_frequencies"] = dict(results["journal_frequencies"])
    results["publication_years"] = dict(results["publication_years"])
    results["passage_distribution"] = dict(results["passage_distribution"])
    results["publication_doc_lists"] = dict(results["publication_doc_lists"])
    results["publications_by_year"] = dict(results["publications_by_year"])

    return results
