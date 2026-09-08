"""Decide which converter to use, page by page. Deterministic, no model."""
from pathlib import Path

import pymupdf

CHAR_THRESHOLD = 120


def route_page(n_chars: int, has_table: bool) -> str:
    """native (pymupdf4llm, fast) | complex (docling) | ocr (docling with OCR)."""
    if n_chars < CHAR_THRESHOLD:
        return "ocr"
    return "complex" if has_table else "native"


def triage(pdf_path: Path) -> dict[str, list[int]]:
    """Returns {'native': [...], 'complex': [...], 'ocr': [...]} with 1-based pages."""
    route: dict[str, list[int]] = {"native": [], "complex": [], "ocr": []}
    with pymupdf.open(pdf_path) as doc:
        for number, page in enumerate(doc, start=1):
            n = len(page.get_text().strip())
            has_table = n >= CHAR_THRESHOLD and bool(page.find_tables().tables)
            route[route_page(n, has_table)].append(number)
    return route
