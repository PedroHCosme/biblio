"""One SQLite file per bibliotheca: FTS5 + vectors.

ponytail: brute-force vector search in numpy. For the measured corpus size
it's instant and avoids a native extension dependency.
"""
import sqlite3
from pathlib import Path

import numpy as np

from biblio.embed import DIM, MODEL

DB_FILE = "biblio.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS chunks (
  id         INTEGER PRIMARY KEY,
  doc        TEXT NOT NULL,
  file       TEXT NOT NULL,
  section    TEXT,
  line_start INTEGER NOT NULL,
  line_end   INTEGER NOT NULL,
  text       TEXT NOT NULL,
  vector     BLOB
);
CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(doc);
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
  text, section, content='chunks', content_rowid='id',
  tokenize="unicode61 remove_diacritics 2"
);
"""


def _migrate_schema(con: sqlite3.Connection) -> None:
    """Drop old Portuguese-column tables so they're recreated with new names."""
    try:
        con.execute("SELECT chave FROM config LIMIT 1")
        con.executescript("""
            DROP TABLE IF EXISTS chunks_fts;
            DROP TABLE IF EXISTS chunks;
            DROP TABLE IF EXISTS config;
        """)
    except sqlite3.OperationalError:
        pass


def connect(bibliotheca: Path) -> sqlite3.Connection:
    con = sqlite3.connect(bibliotheca / DB_FILE)
    con.row_factory = sqlite3.Row
    _migrate_schema(con)
    con.executescript(SCHEMA)
    _check_model(con)
    return con


def _check_model(con: sqlite3.Connection) -> None:
    """Vectors from one model compared with another aren't bad results, they're noise."""
    with con:
        saved = con.execute(
            "SELECT value FROM config WHERE key = 'model'").fetchone()
        if saved is None:
            con.execute("INSERT INTO config VALUES('model', ?)", (MODEL,))
        elif saved[0] != MODEL:
            raise SystemExit(
                f"This bibliotheca was indexed with '{saved[0]}', and this biblio uses "
                f"'{MODEL}'. The vectors are not comparable.\n"
                f"Reindex with: biblio add <source> --force")


def replace_document(con: sqlite3.Connection, doc: str, chunks: list[dict],
                     vectors: np.ndarray) -> None:
    """Deletes and reinserts the entire document. Reprocessing never duplicates."""
    with con:
        old = [tuple(r) for r in con.execute(
            "SELECT id, text, section FROM chunks WHERE doc = ?", (doc,))]
        con.executemany("INSERT INTO chunks_fts(chunks_fts, rowid, text, section) "
                        "VALUES('delete', ?, ?, ?)", old)
        con.execute("DELETE FROM chunks WHERE doc = ?", (doc,))
        for chunk, vector in zip(chunks, vectors):
            cursor = con.execute(
                "INSERT INTO chunks(doc, file, section, line_start, line_end, text, vector)"
                " VALUES(?,?,?,?,?,?,?)",
                (doc, chunk["file"], chunk["section"], chunk["line_start"],
                 chunk["line_end"], chunk["text"],
                 np.asarray(vector, dtype="float32").tobytes()),
            )
            con.execute("INSERT INTO chunks_fts(rowid, text, section) VALUES(?,?,?)",
                        (cursor.lastrowid, chunk["text"], chunk["section"]))


def search_fts(con: sqlite3.Connection, query: str, k: int,
               doc: str | None = None) -> list[int]:
    terms = " OR ".join(f'"{t}"' for t in query.split() if t)
    if not terms:
        return []
    sql = ("SELECT c.id FROM chunks_fts f JOIN chunks c ON c.id = f.rowid "
           "WHERE chunks_fts MATCH ?")
    params: list = [terms]
    if doc:
        sql += " AND c.doc = ?"
        params.append(doc)
    sql += " ORDER BY bm25(chunks_fts) LIMIT ?"
    params.append(k)
    return [row["id"] for row in con.execute(sql, params)]


def search_vector(con: sqlite3.Connection, query: np.ndarray, k: int,
                  doc: str | None = None) -> list[int]:
    sql = "SELECT id, vector FROM chunks WHERE vector IS NOT NULL"
    params: list = []
    if doc:
        sql += " AND doc = ?"
        params.append(doc)
    rows = con.execute(sql, params).fetchall()
    if not rows:
        return []
    ids = np.array([row["id"] for row in rows])
    matrix = np.frombuffer(b"".join(row["vector"] for row in rows),
                           dtype="float32").reshape(len(ids), DIM)
    scores = matrix @ np.asarray(query, dtype="float32")
    best = np.argsort(scores)[::-1][:k]
    return [int(ids[i]) for i in best]


def details(con: sqlite3.Connection, ids: list[int]) -> dict[int, sqlite3.Row]:
    if not ids:
        return {}
    placeholders = ",".join("?" * len(ids))
    return {row["id"]: row for row in con.execute(
        f"SELECT id, doc, file, section, line_start, line_end FROM chunks "
        f"WHERE id IN ({placeholders})", ids)}
