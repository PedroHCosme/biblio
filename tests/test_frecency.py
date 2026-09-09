"""Frecency ranking: access recording, scoring, search integration."""
import base64

import numpy as np
import pytest

from biblio import db
from biblio.embed import DIM
from biblio.search import search, rrf
from biblio.cli import main as cli_main
from biblio.skill import skill_text, claude_md_text


@pytest.fixture
def con(tmp_path):
    return db.connect(tmp_path)


# --- Task 1: schema + session counter ---

def test_accesses_table_exists(con):
    tables = {r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert "accesses" in tables


def test_session_counter_starts_at_zero(con):
    row = con.execute("SELECT value FROM config WHERE key='session_counter'").fetchone()
    assert row is not None
    assert row[0] == "0"


def test_increment_and_get_session(con):
    assert db.get_session(con) == 0
    db.increment_session(con)
    assert db.get_session(con) == 1
    db.increment_session(con)
    assert db.get_session(con) == 2


# --- Task 2: access recording ---

def _fake_vec_f16():
    """Random normalized vector stored as float16 bytes."""
    v = np.random.randn(DIM).astype("float32")
    v /= np.linalg.norm(v)
    return np.asarray(v, dtype="float16").tobytes()


def _insert_chunk(con, doc="test-doc", file="01-test.md"):
    """Insert a minimal chunk and return its id."""
    con.execute("INSERT OR IGNORE INTO config VALUES('model', 'test')")
    cur = con.execute(
        "INSERT INTO chunks(doc, file, section, line_start, line_end, text) "
        "VALUES(?, ?, 'Test', 1, 10, 'test text')", (doc, file))
    con.commit()
    return cur.lastrowid


def test_record_access_inserts_row(con):
    cid = _insert_chunk(con)
    vec = _fake_vec_f16()
    db.record_access(con, cid, vec, weight=1, session_id=1)
    rows = con.execute("SELECT * FROM accesses WHERE chunk_id = ?", (cid,)).fetchall()
    assert len(rows) == 1
    assert rows[0]["weight"] == 1
    assert rows[0]["session_id"] == 1


def test_record_access_enforces_cap(con):
    cid = _insert_chunk(con)
    for i in range(25):
        db.record_access(con, cid, _fake_vec_f16(), weight=1, session_id=i)
    rows = con.execute("SELECT * FROM accesses WHERE chunk_id = ?", (cid,)).fetchall()
    assert len(rows) == 20
    sessions = [r["session_id"] for r in rows]
    assert min(sessions) == 5, "oldest records should be evicted"


def test_save_and_get_last_query_vec(con):
    vec = _fake_vec_f16()
    db.save_last_query_vec(con, vec)
    loaded = db.get_last_query_vec(con)
    assert loaded == vec


def test_get_last_query_vec_returns_none_when_empty(con):
    assert db.get_last_query_vec(con) is None


def test_float16_roundtrip_preserves_similarity():
    v = np.random.randn(DIM).astype("float32")
    v /= np.linalg.norm(v)
    stored = np.asarray(v, dtype="float16").tobytes()
    loaded = np.frombuffer(stored, dtype="float16").astype("float32")
    sim = float(v @ loaded / (np.linalg.norm(v) * np.linalg.norm(loaded)))
    assert sim > 0.99, f"float16 roundtrip destroyed similarity: {sim}"


# --- Task 3: frecency scoring and ranking ---

def _make_access(id_, query_vec_f32, weight, session_id):
    """Simulates an access row dict for frecency_score."""
    vec_f16 = np.asarray(query_vec_f32, dtype="float16").tobytes()
    return {"id": id_, "query_vec": vec_f16, "weight": weight,
            "session_id": session_id}


def test_frecency_score_basic():
    v = np.random.randn(DIM).astype("float32")
    v /= np.linalg.norm(v)
    acc = _make_access(1, v, weight=5, session_id=10)
    score, prune = db.frecency_score([acc], v, current_session=10)
    assert score > 0
    assert prune == []


def test_frecency_score_zero_for_unrelated_query():
    v1 = np.zeros(DIM, dtype="float32"); v1[0] = 1.0
    v2 = np.zeros(DIM, dtype="float32"); v2[1] = 1.0
    acc = _make_access(1, v1, weight=1, session_id=10)
    score, _ = db.frecency_score([acc], v2, current_session=10)
    assert score == 0.0, "orthogonal vectors should produce zero score"


def test_frecency_score_decays_with_age():
    v = np.random.randn(DIM).astype("float32")
    v /= np.linalg.norm(v)
    recent = _make_access(1, v, weight=1, session_id=10)
    old = _make_access(2, v, weight=1, session_id=3)
    score_recent, _ = db.frecency_score([recent], v, current_session=10)
    score_old, _ = db.frecency_score([old], v, current_session=10)
    assert score_recent > score_old


def test_frecency_score_hit_beats_search():
    v = np.random.randn(DIM).astype("float32")
    v /= np.linalg.norm(v)
    hit = _make_access(1, v, weight=5, session_id=10)
    search_acc = _make_access(2, v, weight=1, session_id=10)
    score_hit, _ = db.frecency_score([hit], v, current_session=10)
    score_search, _ = db.frecency_score([search_acc], v, current_session=10)
    assert score_hit > score_search


def test_frecency_score_prunes_negligible():
    v = np.random.randn(DIM).astype("float32")
    v /= np.linalg.norm(v)
    ancient = _make_access(99, v, weight=1, session_id=0)
    _, prune = db.frecency_score([ancient], v, current_session=200)
    assert 99 in prune, "ancient record should be pruned"


def test_frecency_empty_accesses():
    v = np.random.randn(DIM).astype("float32")
    v /= np.linalg.norm(v)
    score, prune = db.frecency_score([], v, current_session=10)
    assert score == 0.0
    assert prune == []


def test_ranked_by_frecency_returns_scored_chunks(con):
    cid1 = _insert_chunk(con, doc="doc-a", file="01-a.md")
    cid2 = _insert_chunk(con, doc="doc-b", file="01-b.md")
    v = np.random.randn(DIM).astype("float32")
    v /= np.linalg.norm(v)
    vec_f16 = np.asarray(v, dtype="float16").tobytes()
    db.increment_session(con)
    for _ in range(3):
        db.record_access(con, cid1, vec_f16, weight=5, session_id=1)
    db.record_access(con, cid2, vec_f16, weight=1, session_id=1)
    ranked = db.ranked_by_frecency(con, v, candidates=10)
    ids = [cid for cid, _ in ranked]
    assert ids[0] == cid1, "chunk with more/heavier accesses should rank first"
    assert cid2 in ids


def test_ranked_by_frecency_empty_when_no_accesses(con):
    assert db.ranked_by_frecency(con, np.zeros(DIM, dtype="float32"), candidates=10) == []


def test_ranked_by_frecency_returns_scores(con):
    """ranked_by_frecency returns (chunk_id, score) tuples."""
    cid = _insert_chunk(con, doc="doc-s", file="01-s.md")
    v = np.random.randn(DIM).astype("float32")
    v /= np.linalg.norm(v)
    vec_f16 = np.asarray(v, dtype="float16").tobytes()
    db.increment_session(con)
    db.record_access(con, cid, vec_f16, weight=5, session_id=1)
    ranked = db.ranked_by_frecency(con, v, candidates=10)
    assert len(ranked) >= 1
    assert isinstance(ranked[0], tuple), "should return (chunk_id, score) tuples"
    assert len(ranked[0]) == 2
    chunk_id, score = ranked[0]
    assert chunk_id == cid
    assert score > 0


# --- Task 4: search integration ---

def test_frecency_boosts_accessed_chunk(synthetic_bibliotheca):
    """After hitting a chunk multiple times, it should rank higher on similar queries."""
    query = "comprimento de ancoragem"
    baseline = search(query, output=synthetic_bibliotheca, top=5)
    assert baseline, "search must return results"

    con = db.connect(synthetic_bibliotheca)
    try:
        vec = np.frombuffer(
            db.get_last_query_vec(con), dtype="float16").astype("float32")
        top_file = baseline[0]["file"]
        row = con.execute(
            "SELECT id FROM chunks WHERE file = ? LIMIT 1",
            (top_file,)).fetchone()
        assert row, f"chunk for {top_file} not found"
        cid = row["id"]
        vec_f16 = np.asarray(vec, dtype="float16").tobytes()
        session = db.get_session(con)
        for _ in range(5):
            db.record_access(con, cid, vec_f16, weight=5, session_id=session)
    finally:
        con.close()

    boosted = search(query, output=synthetic_bibliotheca, top=5)
    assert boosted[0]["file"] == top_file


def test_no_frecency_flag_skips_recording(tmp_path):
    """With no_frecency=True, no access recording or last_query_vec saving."""
    from biblio import embed
    con = db.connect(tmp_path)
    con.execute("INSERT OR IGNORE INTO config VALUES('model', ?)", (embed.MODEL,))
    con.commit()
    con.close()

    search("test", output=tmp_path, top=5, no_frecency=True)
    con = db.connect(tmp_path)
    try:
        assert db.get_session(con) == 0, "search never increments session"
        rows = con.execute("SELECT COUNT(*) FROM accesses").fetchone()[0]
        assert rows == 0, "no accesses should be recorded with no_frecency"
    finally:
        con.close()


def test_search_does_not_increment_session(tmp_path):
    """search() should no longer increment the session counter."""
    from biblio import embed
    con = db.connect(tmp_path)
    con.execute("INSERT OR IGNORE INTO config VALUES('model', ?)", (embed.MODEL,))
    con.commit()
    con.close()

    search("test query", output=tmp_path, top=5)
    search("another query", output=tmp_path, top=5)

    con = db.connect(tmp_path)
    try:
        assert db.get_session(con) == 0, \
            "search should not increment session counter"
    finally:
        con.close()


def test_search_fusion_mode_flat(synthetic_bibliotheca):
    """fusion_mode='flat' should work (current default behavior)."""
    results = search("ancoragem", output=synthetic_bibliotheca, top=5,
                     fusion_mode="flat")
    assert results


def test_search_fusion_mode_weighted(synthetic_bibliotheca):
    """fusion_mode='weighted' should work without error."""
    results = search("ancoragem", output=synthetic_bibliotheca, top=5,
                     fusion_mode="weighted")
    assert results


def test_search_fusion_mode_bonus(synthetic_bibliotheca):
    """fusion_mode='bonus' should work without error."""
    results = search("ancoragem", output=synthetic_bibliotheca, top=5,
                     fusion_mode="bonus")
    assert results


def test_search_fusion_weighted_and_bonus_run_frecency_math(synthetic_bibliotheca):
    """The other fusion tests never populate accesses, so the weighted-weight and
    bonus-additive code paths never execute. This one records real accesses so
    `all_frecency_scores` is non-empty and the frec_weight / bonus formulas run."""
    query = "comprimento de ancoragem"
    baseline = search(query, output=synthetic_bibliotheca, top=5)
    assert baseline, "search must return results"
    top_file = baseline[0]["file"]

    con = db.connect(synthetic_bibliotheca)
    try:
        vec = np.frombuffer(
            db.get_last_query_vec(con), dtype="float16").astype("float32")
        row = con.execute(
            "SELECT id FROM chunks WHERE file = ? LIMIT 1", (top_file,)).fetchone()
        assert row, f"chunk for {top_file} not found"
        cid = row["id"]
        vec_f16 = np.asarray(vec, dtype="float16").tobytes()
        session = db.get_session(con)
        for _ in range(5):
            db.record_access(con, cid, vec_f16, weight=5, session_id=session)
    finally:
        con.close()

    for mode in ("weighted", "bonus"):
        res = search(query, output=synthetic_bibliotheca, top=5, fusion_mode=mode)
        assert res, f"fusion_mode={mode} returned no results"
        files = [r["file"] for r in res]
        assert top_file in files, f"{mode}: heavily-accessed file dropped out"
        assert files.index(top_file) == 0, \
            f"{mode}: frecency math did not keep the boosted file on top"


def test_search_record_appearances_false(tmp_path):
    """record_appearances=False should skip access recording in search."""
    from biblio import embed
    con = db.connect(tmp_path)
    con.execute("INSERT OR IGNORE INTO config VALUES('model', ?)", (embed.MODEL,))
    con.commit()
    con.close()

    search("test", output=tmp_path, top=5, record_appearances=False)

    con = db.connect(tmp_path)
    try:
        rows = con.execute("SELECT COUNT(*) FROM accesses").fetchone()[0]
        assert rows == 0, "no accesses should be recorded with record_appearances=False"
    finally:
        con.close()


# --- Task 5: CLI ---

def test_cli_hit_records_access(synthetic_bibliotheca, monkeypatch):
    """biblio hit should record a weight-5 access."""
    monkeypatch.setattr("biblio.paths.REGISTRY",
                        synthetic_bibliotheca.parent / "bibliothecas.txt")
    cli_main(["search", "ancoragem", "--lib", str(synthetic_bibliotheca)])

    con = db.connect(synthetic_bibliotheca)
    try:
        row = con.execute(
            "SELECT doc, file, line_start, line_end FROM chunks LIMIT 1"
        ).fetchone()
        filepath = str((synthetic_bibliotheca / row["doc"] / row["file"]).resolve())
        pointer = f"{filepath}:{row['line_start']}-{row['line_end']}"
    finally:
        con.close()

    result = cli_main(["hit", pointer])
    assert result == 0

    con = db.connect(synthetic_bibliotheca)
    try:
        hits = con.execute(
            "SELECT weight FROM accesses WHERE weight = 5").fetchall()
        assert len(hits) >= 1, "hit should record weight-5 access"
    finally:
        con.close()


def test_cli_hit_accepts_section_pointer(synthetic_bibliotheca, monkeypatch):
    """A pointer straight from `biblio search` output (section interval, starts
    at line 1) must resolve to the file's chunk, not fail on line_start."""
    monkeypatch.setattr("biblio.paths.REGISTRY",
                        synthetic_bibliotheca.parent / "bibliothecas.txt")
    results = search("ancoragem", output=synthetic_bibliotheca, top=1)
    assert results
    pointer = f"{results[0]['path']}:{results[0]['line_start']}-{results[0]['line_end']}"
    assert pointer.split(":")[-1].startswith("1-")  # section interval
    assert cli_main(["hit", pointer]) == 0

    con = db.connect(synthetic_bibliotheca)
    try:
        assert con.execute(
            "SELECT COUNT(*) FROM accesses WHERE weight = 5").fetchone()[0] >= 1
    finally:
        con.close()


def test_cli_hit_increments_session(synthetic_bibliotheca, monkeypatch):
    """biblio hit should increment the session counter."""
    monkeypatch.setattr("biblio.paths.REGISTRY",
                        synthetic_bibliotheca.parent / "bibliothecas.txt")
    cli_main(["search", "ancoragem", "--lib", str(synthetic_bibliotheca)])

    con = db.connect(synthetic_bibliotheca)
    try:
        session_before = db.get_session(con)
        row = con.execute(
            "SELECT doc, file, line_start, line_end FROM chunks LIMIT 1"
        ).fetchone()
        filepath = str((synthetic_bibliotheca / row["doc"] / row["file"]).resolve())
        pointer = f"{filepath}:{row['line_start']}-{row['line_end']}"
    finally:
        con.close()

    cli_main(["hit", pointer])

    con = db.connect(synthetic_bibliotheca)
    try:
        assert db.get_session(con) == session_before + 1, \
            "hit should increment session counter"
    finally:
        con.close()


def test_cli_no_frecency_flag(synthetic_bibliotheca, capsys):
    result = cli_main(["search", "ancoragem",
                       "--lib", str(synthetic_bibliotheca),
                       "--no-frecency"])
    assert result == 0


# --- Task 6: skill protocol ---

def test_skill_text_includes_hit_step():
    text = skill_text()
    assert "hit" in text
    assert "Found what you needed" in text


def test_claude_md_includes_hit_step():
    text = claude_md_text()
    assert "hit" in text


def test_protocol_step_numbering():
    text = skill_text()
    assert "**1." in text
    assert "**2." in text
    assert "**3." in text
    assert "**4." in text
    assert "**5." in text


# --- Weighted RRF and fusion constants ---

def test_rrf_with_weights():
    """Weighted list should contribute more than unweighted."""
    list_a = ["x", "y", "z"]
    list_b = ["y", "x", "z"]
    # Equal weights = default behavior
    equal = rrf([list_a, list_b])
    # list_b weight=3 should boost "y" relative to "x"
    weighted = rrf([list_a, list_b], weights=[1.0, 3.0])
    assert weighted["y"] > weighted["x"], \
        "y is rank-1 in the 3x-weighted list, should beat x"
    assert equal["y"] == pytest.approx(equal["x"]), \
        "without weights, x and y tie (each rank-1 in one list)"


def test_rrf_weights_none_is_default():
    """weights=None should produce identical results to no-arg call."""
    lists = [["a", "b"], ["b", "a"]]
    assert rrf(lists) == rrf(lists, weights=None)
