"""Embeddings: modelo e dimensao decididos por medicao na Tarefa 0.3.

A unidade e a janela dentro do arquivo, nao o arquivo (spec 4.6). A janela
avanca por linha inteira para que o ponteiro linha_ini-linha_fim seja exato.
"""
import functools
import re
from pathlib import Path

import numpy as np

MODELO = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DIM = 384
PREFIXO_CONSULTA = ""  # so a familia e5 precisa; descartada no spike (errou 2/4 casos cruzados)
PREFIXO_DOC = ""

JANELA = 2000       # ~500 tokens (spec risco 5); caracteres, nao tokens: nao precisa tokenizar
SOBREPOSICAO = 200  # evita cortar exatamente no meio da frase que responde a consulta

_FRONTMATTER = re.compile(r"\A---\n.*?\n---\n", re.S)


@functools.lru_cache(maxsize=1)
def _modelo():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(MODELO)


def janelas(texto: str, primeira_linha: int = 1) -> list[dict]:
    """Fatia por linhas ate encher a janela. Devolve texto + ponteiro 1-based inclusivo."""
    linhas = texto.split("\n")
    saida, inicio = [], 0
    while inicio < len(linhas):
        fim, tamanho = inicio, 0
        while fim < len(linhas) and (tamanho == 0 or tamanho + len(linhas[fim]) <= JANELA):
            tamanho += len(linhas[fim]) + 1
            fim += 1
        bloco = "\n".join(linhas[inicio:fim]).strip()
        if bloco:
            saida.append({"texto": bloco,
                          "linha_ini": primeira_linha + inicio,
                          "linha_fim": primeira_linha + fim - 1})
        if fim >= len(linhas):
            break
        recuo = 0
        while recuo < fim - inicio - 1 and sum(
                len(l) + 1 for l in linhas[fim - recuo - 1:fim]) < SOBREPOSICAO:
            recuo += 1
        inicio = fim - recuo
    return saida


def chunks_do_documento(pasta_doc: Path) -> list[dict]:
    chunks = []
    for arquivo in sorted(pasta_doc.glob("[0-9]*.md")):
        conteudo = arquivo.read_text(encoding="utf-8")
        # o frontmatter nao entra no embedding, mas conta nas linhas do ponteiro
        corpo = _FRONTMATTER.sub("", conteudo)
        deslocamento = conteudo[:len(conteudo) - len(corpo)].count("\n") + 1
        secao = next((l for l in corpo.split("\n") if l.startswith("#")), arquivo.stem)
        for janela in janelas(corpo, primeira_linha=deslocamento):
            chunks.append(janela | {"arquivo": arquivo.name, "secao": secao.lstrip("# ")})
    return chunks


def vetorizar(textos: list[str]) -> np.ndarray:
    """Vetoriza trechos do acervo. Prefixo de documento, nao de consulta."""
    if not textos:
        return np.empty((0, DIM), dtype="float32")
    return _modelo().encode([PREFIXO_DOC + t for t in textos],
                            normalize_embeddings=True,
                            batch_size=16).astype("float32")


def vetorizar_consulta(consulta: str) -> np.ndarray:
    """Prefixo diferente do de documento: e assim que a familia e5 foi treinada, e
    trocar os dois derruba a qualidade sem dar erro nenhum. Vazio nos outros modelos.
    """
    return _modelo().encode([PREFIXO_CONSULTA + consulta], normalize_embeddings=True,
                            batch_size=1).astype("float32")[0]
