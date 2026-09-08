"""Embeddings: model and dimension decided by measurement."""
import functools
import re
from pathlib import Path

import numpy as np

MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DIM = 384
QUERY_PREFIX = ""
DOC_PREFIX = ""

WINDOW = 2000
OVERLAP = 200

_FRONTMATTER = re.compile(r"\A---\n.*?\n---\n", re.S)


@functools.lru_cache(maxsize=1)
def _model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(MODEL)


def windows(text: str, first_line: int = 1) -> list[dict]:
    """Slice by lines until the window is full. Returns text + 1-based inclusive pointer."""
    lines = text.split("\n")
    result, start = [], 0
    while start < len(lines):
        end, size = start, 0
        while end < len(lines) and (size == 0 or size + len(lines[end]) <= WINDOW):
            size += len(lines[end]) + 1
            end += 1
        block = "\n".join(lines[start:end]).strip()
        if block:
            result.append({"text": block,
                           "line_start": first_line + start,
                           "line_end": first_line + end - 1})
        if end >= len(lines):
            break
        rewind = 0
        while rewind < end - start - 1 and sum(
                len(l) + 1 for l in lines[end - rewind - 1:end]) < OVERLAP:
            rewind += 1
        start = end - rewind
    return result


def doc_chunks(doc_dir: Path) -> list[dict]:
    chunks = []
    for f in sorted(doc_dir.glob("[0-9]*.md")):
        content = f.read_text(encoding="utf-8")
        body = _FRONTMATTER.sub("", content)
        offset = content[:len(content) - len(body)].count("\n") + 1
        section = next((l for l in body.split("\n") if l.startswith("#")), f.stem)
        for win in windows(body, first_line=offset):
            chunks.append(win | {"file": f.name, "section": section.lstrip("# ")})
    return chunks


def vectorize(texts: list[str]) -> np.ndarray:
    """Vectorize corpus chunks. Document prefix, not query prefix."""
    if not texts:
        return np.empty((0, DIM), dtype="float32")
    return _model().encode([DOC_PREFIX + t for t in texts],
                           normalize_embeddings=True,
                           batch_size=16).astype("float32")


def vectorize_query(query: str) -> np.ndarray:
    return _model().encode([QUERY_PREFIX + query], normalize_embeddings=True,
                           batch_size=1).astype("float32")[0]
