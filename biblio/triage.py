"""Decide, pagina a pagina, qual conversor usar. Deterministico, sem modelo."""
from pathlib import Path

import pymupdf

# spec 4.1: abaixo disso a pagina e tratada como imagem (OCR).
# Medido no acervo ELE085: 108 das 182 paginas roteadas para OCR com o corte em 200
# tinham 120-199 caracteres nativos — e esse texto ERA o conteudo do slide (bullets
# e equacoes). OCR delas relia os mesmos bullets a ~8s/pagina. Baixado para 120:
# ingestao de uma aula OCR-pesada caiu 144s->82s, com MAIS texto indexado.
# Slide com 120-199 ch nativos passa direto; scan de verdade (pagina quase vazia,
# < 120) ainda vai para OCR.
LIMIAR_CARACTERES = 120


def rotear_pagina(n_caracteres: int, tem_tabela: bool) -> str:
    """nativa (pymupdf4llm, rapido) | complexa (docling) | ocr (docling com OCR)."""
    if n_caracteres < LIMIAR_CARACTERES:
        return "ocr"
    return "complexa" if tem_tabela else "nativa"


def triar(caminho_pdf: Path) -> dict[str, list[int]]:
    """Devolve {'nativa': [...], 'complexa': [...], 'ocr': [...]} com paginas 1-based."""
    rota: dict[str, list[int]] = {"nativa": [], "complexa": [], "ocr": []}
    with pymupdf.open(caminho_pdf) as doc:
        for numero, pagina in enumerate(doc, start=1):
            n = len(pagina.get_text().strip())
            # ponytail: find_tables() so roda quando a pagina ja passou no limiar;
            # e a chamada cara da triagem e nao muda o resultado das paginas de OCR.
            tem_tabela = n >= LIMIAR_CARACTERES and bool(pagina.find_tables().tables)
            rota[rotear_pagina(n, tem_tabela)].append(numero)
    return rota
