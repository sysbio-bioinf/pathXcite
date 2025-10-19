"""Validate enrichment result TSV files for correct format and content"""

# --- Standard Library Imports ---
import csv
import os
import re

# --- Constants ---
HEADER = [
    "Term", "Overlap", "P-value", "Odds Ratio", "Z-Score",
    "Combined Score", "Adjusted P-value", "Genes"
]

_OVERLAP_RE = re.compile(r"^\s*(\d+)\s*/\s*(\d+)\s*$")

# permissive but disallows blanks/whitespace
_GENE_TOKEN_RE = re.compile(r"^[A-Za-z0-9._-]+$")


# --- Public Functions ---
def validate_tsv_file(filepath: str) -> tuple[bool, list[str]]:
    """
    Validate that a TSV file:
      1) exists and has .tsv extension
      2) has the exact expected header
      3) each row's values match required types and consistency rules.

    Args:
        filepath (str): Path to the TSV file.

    Returns:
        tuple[bool, list[str]]: (is_valid, list_of_error_messages)
    """
    errors: list[str] = []

    # 1) path and extension
    if not os.path.isfile(filepath):
        return False, [f"File not found: {filepath}"]
    if not filepath.lower().endswith(".tsv"):
        return False, [f"Not a .tsv file: {filepath}"]

    # 2) read & header
    try:
        with open(filepath, "r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f, delimiter="\t")
            header = next(reader, None)
            if header != HEADER:
                return False, [f"Header mismatch.\nExpected: {HEADER}\nFound:    {header}"]

            # 3) validate rows
            # line numbers (header is line 1)
            for idx, row in enumerate(reader, start=2):
                if len(row) != len(HEADER):
                    errors.append(
                        f"Line {idx}: expected {len(HEADER)} columns, found {len(row)}.")
                    continue

                (term, overlap, pval, odds_ratio, zscore,
                 combined_score, adj_pval, genes) = row

                term_size = overlap.split(
                    "/")[1] if overlap and "/" in overlap else None
                query_size = overlap.split(
                    "/")[0] if overlap and "/" in overlap else None

                # background_size
                # Term
                if not term or not term.strip():
                    errors.append(f"Line {idx}: 'Term' is empty.")

                # Overlap 'a/b'
                m = _OVERLAP_RE.match(overlap or "")
                if not m:
                    errors.append(
                        f"Line {idx}: 'Overlap' must be of form 'a/b' with integers. Got '{overlap}'.")
                    a = b = None
                else:
                    a, b = int(m.group(1)), int(m.group(2))

                # Int columns
                for col_name, val in [
                    ("Term Size", term_size),
                    ("Query Size", query_size)
                ]:
                    if not _is_int(val):
                        errors.append(
                            f"Line {idx}: '{col_name}' must be an integer. Got '{val}'.")

                # Only convert after recording type errors
                try:
                    term_size_i = int(term_size)
                    query_size_i = int(query_size)
                except Exception:
                    # Skip further relational checks for this row
                    continue

                # Non-negative checks
                for col_name, val in [
                    ("Term Size", term_size_i),
                    ("Query Size", query_size_i)
                ]:
                    if val < 0:
                        errors.append(
                            f"Line {idx}: '{col_name}' must be ≥ 0. Got {val}.")

                # Overlap consistency if parsed
                if m:
                    if b != term_size_i:
                        errors.append(
                            f"Line {idx}: Overlap denominator ({b}) != Term Size ({term_size_i}).")
                    if a > b:
                        errors.append(
                            f"Line {idx}: Overlap numerator ({a}) cannot exceed denominator ({b}).")

                # Floats (no NaN/Inf via regex)
                for col_name, val in [
                    ("P-value", pval),
                    ("Odds Ratio", odds_ratio),
                    ("Z-Score", zscore),
                    ("Combined Score", combined_score),
                    ("Adjusted P-value", adj_pval)
                ]:
                    if not _is_float(val):
                        errors.append(
                            f"Line {idx}: '{col_name}' must be numeric (supports scientific notation). Got '{val}'.")

                # Genes: semicolon-separated tokens, no empty entries, valid chars
                gene_tokens = [g.strip() for g in (genes or "").split(";")]
                if len(gene_tokens) == 0 or any(g == "" for g in gene_tokens):
                    errors.append(
                        f"Line {idx}: 'Genes' must be a ';'-separated list with no empty entries.")
                else:
                    for g in gene_tokens:
                        if not _GENE_TOKEN_RE.match(g):
                            errors.append(
                                f"Line {idx}: gene token '{g}' contains invalid characters.")

    except Exception as e:
        return False, [f"Failed to read/parse file: {e}"]

    return (len(errors) == 0), errors


# --- Private Functions ---
def _is_int(val) -> bool:
    """Check if a value can be converted to an integer."""
    try:
        int(val)
        return True
    except (TypeError, ValueError):
        return False


def _is_float(val) -> bool:
    """Check if a value can be converted to a float (not NaN/Inf)."""
    try:
        f = float(val)
        if f == float("inf") or f == float("-inf") or f != f:  # check for inf/nan
            return False
        return True
    except (TypeError, ValueError):
        return False
