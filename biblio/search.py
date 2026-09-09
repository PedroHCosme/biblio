"""Hybrid search. Returns path, lines, score, and heading. Never the body."""
import re
import unicodedata
from math import exp
from pathlib import Path

import numpy as np

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


def rrf(lists: list[list], weights: list[float] | None = None) -> dict:
    """1/(K + position) per list, summed. Optional per-list weights."""
    scores: dict = {}
    for i, lst in enumerate(lists):
        w = weights[i] if weights else 1.0
        for position, key in enumerate(lst, start=1):
            scores[key] = scores.get(key, 0.0) + w / (K_RRF + position)
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
           context: str = "section", no_frecency: bool = False,
           fusion_mode: str = "flat",
           record_appearances: bool = True) -> list[dict]:
    """Covers all registered bibliothecas, unless `output` (path or list) restricts."""
    # Three fusion modes (flat/weighted/bonus) compete here for a benchmark to
    # pick one. Temporary: Task 7 deletes the losers and the
    # fusion_mode / record_appearances params.
    candidates = top * MULTIPLE
    vector = embed.vectorize_query(query)
    vec_f16 = np.asarray(vector, dtype="float16").tobytes()

    lists: list[list] = []
    rows: dict = {}
    all_frecency_scores: dict[tuple, float] = {}
    list_is_frecency: list[bool] = []
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

            if not no_frecency:
                frecency_ranked = db.ranked_by_frecency(con, vector, candidates, doc)
                if frecency_ranked:
                    for cid, sc in frecency_ranked:
                        all_frecency_scores[(bibliotheca, cid)] = sc
                    if fusion_mode in ("flat", "weighted"):
                        rankings.append([cid for cid, _ in frecency_ranked])

            for chunk_id, row in db.details(
                    con, list({i for r in rankings for i in r})).items():
                rows[(bibliotheca, chunk_id)] = row
            for j, r in enumerate(rankings):
                lists.append([(bibliotheca, i) for i in r])
                list_is_frecency.append(j == 2)  # rankings = [vector, fts, frecency?]; frecency is always index 2
        finally:
            con.close()

    q_tokens = _tokens(query)
    if fusion_mode == "weighted" and all_frecency_scores:
        max_frec = max(all_frecency_scores.values())
        frec_weight = db.BASE_WEIGHT * (1 - exp(-max_frec / db.FRECENCY_SCALE))
        weights = [frec_weight if is_frec else 1.0 for is_frec in list_is_frecency]
        scored = rrf(lists, weights=weights)
    else:
        scored = rrf(lists)

    # bonus mode is asymmetric: it only REORDERS candidates already retrieved by
    # vector/FTS (frecency ids were never appended to `rankings` nor fetched via
    # db.details). flat/weighted instead let a frecency-only chunk enter results.
    if fusion_mode == "bonus":
        for key in list(scored):
            if key in all_frecency_scores:
                bonus = min(all_frecency_scores[key] / db.BONUS_SCALE, db.MAX_BONUS)
                scored[key] += bonus

    if q_tokens:
        for key, row in rows.items():
            match = q_tokens & _tokens(row["section"] or "")
            if match:
                scored[key] = scored.get(key, 0.0) + \
                    BONUS_HEADING * len(match) / len(q_tokens)

    results: list[dict] = []
    result_keys: list[tuple[Path, int]] = []
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
        result_keys.append((bibliotheca, chunk_id))
        if len(results) == top:
            break

    if not no_frecency and record_appearances and result_keys:
        by_lib: dict[Path, list[int]] = {}
        for bib, cid in result_keys:
            by_lib.setdefault(bib, []).append(cid)
        for bib, cids in by_lib.items():
            con = db.connect(bib)
            try:
                session = db.get_session(con)
                for cid in cids:
                    db.record_access(con, cid, vec_f16, weight=1,
                                     session_id=session)
                db.save_last_query_vec(con, vec_f16)
            finally:
                con.close()

    return results


def format_results(results: list[dict]) -> str:
    if not results:
        return "no results"
    return "\n".join(
        f"{r['path']}:{r['line_start']}-{r['line_end']}"
        f"  {r['score']:.3f}  {r['section']}"
        for r in results
    )
