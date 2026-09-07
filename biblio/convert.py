"""Roda o conversor certo por pagina e devolve um markdown unico com marcadores.

O marcador `<!-- pag N -->` sobrevive a normalizacao e e consumido (e removido)
pelo slice, que o usa para preencher `paginas` no frontmatter.
"""
from pathlib import Path

import pymupdf
import pymupdf4llm

MARCADOR = "<!-- pag {} -->"


def _converter_nativas(caminho_pdf: Path, paginas: list[int]) -> dict[int, str]:
    if not paginas:
        return {}
    blocos = pymupdf4llm.to_markdown(
        str(caminho_pdf), pages=[p - 1 for p in paginas], page_chunks=True
    )
    # pymupdf4llm 0.0.17+ nomeia a chave `page_number` (1-based), nao `page`.
    return {b["metadata"]["page_number"]: b["text"] for b in blocos}


def _converter_com_docling(caminho_pdf: Path, paginas: list[int], ocr: bool,
                           device: str) -> dict[int, str]:
    """Docling nao aceita subconjunto de paginas, entao cada pagina vira um PDF de uma folha.

    ponytail: uma folha por chamada e mais lento que um lote, mas o custo real e o OCR,
    nao o setup. Se virar gargalo, agrupar paginas contiguas num PDF so.
    """
    if not paginas:
        return {}
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    opcoes = PdfPipelineOptions()
    opcoes.do_ocr = ocr
    opcoes.do_table_structure = True
    if device != "auto":
        opcoes.accelerator_options.device = device

    conversor = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opcoes)}
    )

    saida: dict[int, str] = {}
    with pymupdf.open(caminho_pdf) as origem:
        for numero in paginas:
            recorte = pymupdf.open()
            recorte.insert_pdf(origem, from_page=numero - 1, to_page=numero - 1)
            temporario = caminho_pdf.parent / f".{caminho_pdf.stem}-p{numero}.pdf"
            recorte.save(temporario)
            recorte.close()
            try:
                saida[numero] = conversor.convert(temporario).document.export_to_markdown()
            finally:
                temporario.unlink(missing_ok=True)
    return saida


def converter(caminho_pdf: Path, rota: dict[str, list[int]], device: str = "auto") -> str:
    """Markdown do documento inteiro, paginas em ordem, cada uma precedida do marcador."""
    paginas = {}
    paginas |= _converter_nativas(caminho_pdf, rota["nativa"])
    paginas |= _converter_com_docling(caminho_pdf, rota["complexa"], ocr=False, device=device)
    paginas |= _converter_com_docling(caminho_pdf, rota["ocr"], ocr=True, device=device)

    partes = []
    for numero in sorted(paginas):
        partes.append(MARCADOR.format(numero))
        partes.append(paginas[numero].strip())
    return "\n\n".join(partes) + "\n"
