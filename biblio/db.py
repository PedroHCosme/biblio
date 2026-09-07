"""Um arquivo SQLite dentro da propria biblioteca: FTS5 + vetores.

ponytail: busca vetorial por forca bruta em numpy. Para o tamanho de acervo medido
na Tarefa 0.2 e instantanea e evita a dependencia de extensao nativa. Trocar por
indice ANN so quando a medicao disser que passou do orcamento.
"""
import sqlite3
from pathlib import Path

import numpy as np

from biblio.embed import DIM, MODELO

ARQUIVO = "biblio.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS config (chave TEXT PRIMARY KEY, valor TEXT);
CREATE TABLE IF NOT EXISTS chunks (
  id        INTEGER PRIMARY KEY,
  doc       TEXT NOT NULL,
  arquivo   TEXT NOT NULL,
  secao     TEXT,
  linha_ini INTEGER NOT NULL,
  linha_fim INTEGER NOT NULL,
  texto     TEXT NOT NULL,
  vetor     BLOB
);
CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(doc);
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
  texto, secao, content='chunks', content_rowid='id',
  tokenize="unicode61 remove_diacritics 2"
);
"""


def conectar(biblioteca: Path) -> sqlite3.Connection:
    con = sqlite3.connect(biblioteca / ARQUIVO)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    _conferir_modelo(con)
    return con


def _conferir_modelo(con: sqlite3.Connection) -> None:
    """Vetor de um modelo comparado com vetor de outro nao e resultado ruim, e ruido.

    Sem esta trava, trocar o modelo — ou abrir numa maquina cuja versao do biblio usa
    outro — devolve ponteiros confiantes e errados, sem erro nenhum. Falhar alto e a
    unica saida honesta: reindexar e barato, resposta errada de norma tecnica nao e.
    """
    with con:
        gravado = con.execute(
            "SELECT valor FROM config WHERE chave = 'modelo'").fetchone()
        if gravado is None:
            con.execute("INSERT INTO config VALUES('modelo', ?)", (MODELO,))
        elif gravado[0] != MODELO:
            raise SystemExit(
                f"Esta biblioteca foi indexada com '{gravado[0]}', e este biblio usa "
                f"'{MODELO}'. Os vetores nao sao comparaveis.\n"
                f"Reindexe com: biblio add <origem> --force")


def substituir_documento(con: sqlite3.Connection, doc: str, chunks: list[dict],
                         vetores: np.ndarray) -> None:
    """Apaga e reinsere o documento inteiro. Reprocessar nunca duplica.

    O `chunks_fts` e `content='chunks'` (external content): o comando 'delete' exige
    os valores **atualmente indexados**, nao strings vazias. Com '' o indice guarda os
    termos antigos apontando para linhas novas, e a busca devolve ponteiro valido com
    conteudo errado — sem erro, e com `integrity-check` passando.
    """
    with con:
        antigos = [tuple(r) for r in con.execute(
            "SELECT id, texto, secao FROM chunks WHERE doc = ?", (doc,))]
        con.executemany("INSERT INTO chunks_fts(chunks_fts, rowid, texto, secao) "
                        "VALUES('delete', ?, ?, ?)", antigos)
        con.execute("DELETE FROM chunks WHERE doc = ?", (doc,))
        for chunk, vetor in zip(chunks, vetores):
            cursor = con.execute(
                "INSERT INTO chunks(doc, arquivo, secao, linha_ini, linha_fim, texto, vetor)"
                " VALUES(?,?,?,?,?,?,?)",
                (doc, chunk["arquivo"], chunk["secao"], chunk["linha_ini"],
                 chunk["linha_fim"], chunk["texto"],
                 np.asarray(vetor, dtype="float32").tobytes()),
            )
            con.execute("INSERT INTO chunks_fts(rowid, texto, secao) VALUES(?,?,?)",
                        (cursor.lastrowid, chunk["texto"], chunk["secao"]))


def buscar_fts(con: sqlite3.Connection, consulta: str, k: int,
               doc: str | None = None) -> list[int]:
    # aspas duplas nos termos: consulta do usuario nao e sintaxe FTS5
    termos = " OR ".join(f'"{t}"' for t in consulta.split() if t)
    if not termos:
        return []
    sql = ("SELECT c.id FROM chunks_fts f JOIN chunks c ON c.id = f.rowid "
           "WHERE chunks_fts MATCH ?")
    parametros: list = [termos]
    if doc:
        sql += " AND c.doc = ?"
        parametros.append(doc)
    sql += " ORDER BY bm25(chunks_fts) LIMIT ?"
    parametros.append(k)
    return [linha["id"] for linha in con.execute(sql, parametros)]


def buscar_vetorial(con: sqlite3.Connection, consulta: np.ndarray, k: int,
                    doc: str | None = None) -> list[int]:
    sql = "SELECT id, vetor FROM chunks WHERE vetor IS NOT NULL"
    parametros: list = []
    if doc:
        sql += " AND doc = ?"
        parametros.append(doc)
    linhas = con.execute(sql, parametros).fetchall()
    if not linhas:
        return []
    ids = np.array([linha["id"] for linha in linhas])
    base = np.frombuffer(b"".join(linha["vetor"] for linha in linhas),
                         dtype="float32").reshape(len(ids), DIM)
    pontos = base @ np.asarray(consulta, dtype="float32")
    melhores = np.argsort(pontos)[::-1][:k]
    return [int(ids[i]) for i in melhores]


def detalhes(con: sqlite3.Connection, ids: list[int]) -> dict[int, sqlite3.Row]:
    if not ids:
        return {}
    marcadores = ",".join("?" * len(ids))
    return {linha["id"]: linha for linha in con.execute(
        f"SELECT id, doc, arquivo, secao, linha_ini, linha_fim FROM chunks "
        f"WHERE id IN ({marcadores})", ids)}
