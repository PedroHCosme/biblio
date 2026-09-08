"""Runs the right converter per page and returns a single markdown with markers."""
from pathlib import Path

import pymupdf
import pymupdf4llm

MARKER = "<!-- pag {} -->"


def _convert_native(pdf_path: Path, pages: list[int]) -> dict[int, str]:
    if not pages:
        return {}
    blocks = pymupdf4llm.to_markdown(
        str(pdf_path), pages=[p - 1 for p in pages], page_chunks=True
    )
    return {b["metadata"]["page_number"]: b["text"] for b in blocks}


def _convert_with_docling(pdf_path: Path, pages: list[int], ocr: bool,
                          device: str, warn=None, label: str = "") -> dict[int, str]:
    """Docling doesn't accept page subsets, so each page becomes a one-page PDF."""
    if not pages:
        return {}
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    options = PdfPipelineOptions()
    options.do_ocr = ocr
    options.do_table_structure = True
    if device != "auto":
        options.accelerator_options.device = device

    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)}
    )

    output: dict[int, str] = {}
    total = len(pages)
    with pymupdf.open(pdf_path) as source:
        for i, number in enumerate(pages, 1):
            if warn:
                warn(f"  {label} page {number} ({i}/{total})")
            excerpt = pymupdf.open()
            excerpt.insert_pdf(source, from_page=number - 1, to_page=number - 1)
            tmp = pdf_path.parent / f".{pdf_path.stem}-p{number}.pdf"
            excerpt.save(tmp)
            excerpt.close()
            try:
                output[number] = converter.convert(tmp).document.export_to_markdown()
            finally:
                tmp.unlink(missing_ok=True)
    return output


def convert(pdf_path: Path, route: dict[str, list[int]], device: str = "auto",
            warn=None, fast: bool = False) -> str:
    """Markdown of the entire document, pages in order, each preceded by a marker.

    fast=True: skips Docling, uses pymupdf4llm for everything. Fast, but scanned
    pages (OCR) come out empty or garbled.
    """
    if fast:
        all_pages = sorted(route["native"] + route["complex"] + route["ocr"])
        pages = _convert_native(pdf_path, all_pages)
    else:
        pages = {}
        pages |= _convert_native(pdf_path, route["native"])
        pages |= _convert_with_docling(pdf_path, route["complex"], ocr=False, device=device,
                                       warn=warn, label="docling")
        pages |= _convert_with_docling(pdf_path, route["ocr"], ocr=True, device=device,
                                       warn=warn, label="ocr")

    parts = []
    for number in sorted(pages):
        parts.append(MARKER.format(number))
        parts.append(pages[number].strip())
    return "\n\n".join(parts) + "\n"
