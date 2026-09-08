"""Hybrid search. Returns path, lines, score, and heading. Never the body."""
import re
import unicodedata
from pathlib import Path

from biblio import db, embed
from biblio.paths import known_bibliothecas, register, all_libs

K_RRF = 60
MULTIPLE = 4
BONUS_HEADING = 0.03

_STOPWORDS = set("o a e de do da os as em para por com como ou no na um uma dos das que "
                 "qual quais entre sobre the of a an is are what how why".split())


def _tokens(text: str) -> set[str]:
    no_accent = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return {t for t in re.findall(r"[a-z0-9]{3,}", no_accent.lower()) if t not in _STOPWORDS}


def rrf(lists: list[list]) -> dict:
    """1/(K + position) per list, summed."""
    scores: dict = {}
    for lst in lists:
        for position, key in enumerate(lst, start=1):
            scores[key] = scores.get(key, 0.0) + 1 / (K_RRF + position)
    return scores


def _interval(filepath: str, row: dict, context: str) -> tuple[int, int]:
    """`window`: just the matched chunk. `section` (default): the entire slice."""
    if context == "window":
        return row["line_start"], row["line_end"]
    try:
        n = len(Path(filepath).read_text(encoding="utf-8", errors="replace").splitlines())
    except OSError:
        return row["line_start"], row["line_end"]
    return 1, n


def search(query: str, output=None, top: int = 5, doc: str | None = None,
           context: str = "section") -> list[dict]:
    """Covers all registered bibliothecas, unless `output` (path or list) restricts."""
    candidates = top * MULTIPLE
    vector = embed.vectorize_query(query)

    lists: list[list] = []
    rows: dict = {}
    for bibliotheca in all_libs(output):
        if not (bibliotheca / db.DB_FILE).exists():
            if output is None:
                continue
            raise SystemExit(
                f'{bibliotheca}: not a biblio bibliotheca (missing {db.DB_FILE}).\n'
                f'Pass the folder path, or a name from `biblio libs`.')
        if output is not None and str(bibliotheca.resolve()) not in known_bibliothecas():
            register(bibliotheca)
        con = db.connect(bibliotheca)
        try:
            rankings = [db.search_vector(con, vector, candidates, doc),
                        db.search_fts(con, query, candidates, doc)]
            for chunk_id, row in db.details(
                    con, list({i for r in rankings for i in r})).items():
                rows[(bibliotheca, chunk_id)] = row
            lists += [[(bibliotheca, i) for i in r] for r in rankings]
        finally:
            con.close()

    q_tokens = _tokens(query)
    scored = rrf(lists)
    if q_tokens:
        for key, row in rows.items():
            match = q_tokens & _tokens(row["section"] or "")
            if match:
                scored[key] = scored.get(key, 0.0) + \
                    BONUS_HEADING * len(match) / len(q_tokens)

    results: list[dict] = []
    seen: set[str] = set()
    for (bibliotheca, chunk_id), score in sorted(scored.items(),
                                                 key=lambda p: -p[1]):
        row = rows.get((bibliotheca, chunk_id))
        if row is None:
            continue
        filepath = str((bibliotheca / row["doc"] / row["file"]).resolve())
        if filepath in seen:
            continue
        seen.add(filepath)
        start, end = _interval(filepath, row, context)
        results.append({
            "path": filepath, "doc": row["doc"], "file": row["file"],
            "section": row["section"], "line_start": start,
            "line_end": end, "score": round(score, 4),
        })
        if len(results) == top:
            break
    return results


def format_results(results: list[dict]) -> str:
    if not results:
        return "no results"
    return "\n".join(
        f"{r['path']}:{r['line_start']}-{r['line_end']}"
        f"  {r['score']:.3f}  {r['section']}"
        for r in results
    )
