#!/usr/bin/env python3
"""Frecency ranking benchmark — 6-config matrix comparison.

Builds a synthetic bibliotheca with confusable topic pairs, warms up
frecency state, then evaluates three fusion modes × two recording modes.
"""
import os
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
try:
    import sys as _sys
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import sys
from math import exp
from pathlib import Path

import numpy as np

# Ensure the project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from biblio import db, embed
from biblio.search import search

# ---------- corpus ----------

CORPUS = {
    "anchorage": (
        "01-anchorage.md",
        "# Anchorage length\n"
        "The basic anchorage length depends on the bond stress between rebar and "
        "concrete. Passive reinforcement bars require a minimum anchorage to develop "
        "the full yield strength. The calculation follows clause 9.4 of the concrete "
        "design standard. Hooked bars reduce the required length. " * 4,
    ),
    "lap_splice": (
        "02-lap-splice.md",
        "# Lap splice\n"
        "The lap splice length for reinforcement bars in tension depends on the bar "
        "diameter and concrete strength. Overlapping bars transfer force through bond "
        "stress. The design standard specifies minimum lap lengths for each bar size. "
        "Bundled bars require increased splice length. " * 4,
    ),
    "nominal_cover": (
        "03-nominal-cover.md",
        "# Nominal cover\n"
        "The nominal concrete cover to reinforcement depends on the environmental "
        "exposure class. Cover protects the rebar from corrosion. Higher exposure "
        "classes require thicker cover. The cover is measured from the surface to the "
        "nearest bar. Minimum values are given in Table 7.2. " * 4,
    ),
    "durability": (
        "04-durability.md",
        "# Durability requirements\n"
        "Durability of concrete structures is governed by exposure class and minimum "
        "cover. Chloride ingress and carbonation are the primary degradation "
        "mechanisms. Water-cement ratio limits and cover requirements work together. "
        "Structures in marine environments need special attention. " * 4,
    ),
    "vfd_soft_start": (
        "05-vfd.md",
        "# VFD soft start\n"
        "A variable frequency drive controls motor speed by varying the supply "
        "frequency. The acceleration ramp reduces inrush current during starting. "
        "The VFD parameters include ramp time, V/f curve, and overload protection. "
        "Three-phase induction motors benefit most from soft starting. " * 4,
    ),
    "direct_on_line": (
        "06-dol.md",
        "# Direct on-line starting\n"
        "Direct on-line starting connects the motor directly to the supply voltage. "
        "The starting current is 6-8 times the rated current. This method is simple "
        "but causes voltage drops and mechanical stress. Star-delta starters reduce "
        "the inrush current to about one-third. " * 4,
    ),
    "shear_links": (
        "07-shear-links.md",
        "# Shear reinforcement\n"
        "Shear links (stirrups) resist diagonal tension in concrete beams. The "
        "spacing depends on the shear force and beam depth. Minimum shear "
        "reinforcement is required even where shear stress is low. Inclined bars "
        "may supplement vertical links. " * 4,
    ),
    "torsion_links": (
        "08-torsion-links.md",
        "# Torsion reinforcement\n"
        "Torsion links form a closed loop around the beam section. The torsional "
        "resistance depends on the enclosed area and the link spacing. Combined "
        "shear and torsion requires superposition of the link areas. Compatibility "
        "torsion may be redistributed. " * 4,
    ),
    "creep": (
        "09-creep.md",
        "# Creep of concrete\n"
        "Creep is the time-dependent strain under sustained load. The creep "
        "coefficient depends on loading age, relative humidity, and member size. "
        "Long-term deflections increase by a factor of 2-3 due to creep. Prestressed "
        "members lose force due to creep shortening. " * 4,
    ),
    "shrinkage": (
        "10-shrinkage.md",
        "# Shrinkage of concrete\n"
        "Drying shrinkage causes volume reduction as moisture evaporates. Autogenous "
        "shrinkage occurs in low water-cement ratio mixes. Restraint of shrinkage "
        "causes cracking. Shrinkage strain depends on humidity, member thickness, "
        "and cement content. " * 4,
    ),
    "weld_fatigue": (
        "11-weld-fatigue.md",
        "# Weld fatigue\n"
        "Fatigue life of welded joints depends on the stress range and detail "
        "category. The S-N curve relates stress range to number of cycles. Weld "
        "toe geometry concentrates stress. Post-weld treatment improves fatigue "
        "life by reducing residual stress. " * 4,
    ),
    "bolt_fatigue": (
        "12-bolt-fatigue.md",
        "# Bolt fatigue\n"
        "High-strength bolts under cyclic loading may fail by fatigue. The fatigue "
        "strength depends on the preload level and stress range. Properly "
        "preloaded bolts in friction connections resist fatigue better than bearing "
        "type. Thread root is the critical location. " * 4,
    ),
}

# 8 unrelated distractors
DISTRACTORS = {
    f"distractor_{i}": (
        f"{i:02d}-filler.md",
        f"# Topic {i}\n"
        f"This document covers unrelated topic number {i}. It contains general "
        f"engineering text that should not match any of the target queries. "
        f"The content is deliberately generic to serve as a distractor. " * 4,
    )
    for i in range(1, 9)
}

# Gold document for each topic (what the correct answer is)
GOLD = {
    "anchorage": "anchorage",
    "lap_splice": "lap_splice",
    "nominal_cover": "nominal_cover",
    "durability": "durability",
    "vfd_soft_start": "vfd_soft_start",
    "direct_on_line": "direct_on_line",
    "shear_links": "shear_links",
    "torsion_links": "torsion_links",
    "creep": "creep",
    "shrinkage": "shrinkage",
    "weld_fatigue": "weld_fatigue",
    "bolt_fatigue": "bolt_fatigue",
}

# Adversarial queries — worded in the sibling's vocabulary
ADVERSARIAL = [
    ("bond stress overlap bars tension", "anchorage"),
    ("minimum length to develop yield in rebar", "anchorage"),
    ("bar diameter concrete strength overlap", "lap_splice"),
    ("transfer force through bond between reinforcement", "lap_splice"),
    ("distance from surface to bar for the exposure class", "nominal_cover"),
    ("protection rebar corrosion table values", "nominal_cover"),
    ("chloride carbonation cover requirements", "durability"),
    ("exposure class minimum protection concrete", "durability"),
    ("motor speed ramp acceleration frequency", "vfd_soft_start"),
    ("reduce inrush current three phase starting", "vfd_soft_start"),
    ("supply voltage starting current six times rated", "direct_on_line"),
    ("star delta voltage drop mechanical stress", "direct_on_line"),
    ("diagonal tension stirrups spacing beam", "shear_links"),
    ("minimum reinforcement inclined bars vertical", "shear_links"),
    ("closed loop section torsional resistance", "torsion_links"),
    ("combined shear superposition link areas", "torsion_links"),
    ("time dependent strain sustained load coefficient", "creep"),
    ("long-term deflection prestressed shortening", "creep"),
    ("volume reduction moisture evaporation drying", "shrinkage"),
    ("restraint cracking cement content humidity", "shrinkage"),
    ("stress range S-N curve detail category", "weld_fatigue"),
    ("post treatment residual stress toe geometry", "weld_fatigue"),
    ("preload level stress range friction connection", "bolt_fatigue"),
    ("thread root cyclic loading high strength", "bolt_fatigue"),
]

# Re-ask queries — the exact phrases used during warm-up
REASK = [
    ("anchorage length bond stress rebar", "anchorage"),
    ("lap splice reinforcement tension", "lap_splice"),
    ("nominal cover exposure class corrosion", "nominal_cover"),
    ("durability chloride carbonation", "durability"),
    ("VFD soft start acceleration ramp", "vfd_soft_start"),
    ("direct on-line starting inrush current", "direct_on_line"),
    ("shear links stirrups diagonal tension", "shear_links"),
    ("torsion links closed loop reinforcement", "torsion_links"),
    ("creep time-dependent strain", "creep"),
    ("shrinkage drying autogenous", "shrinkage"),
    ("weld fatigue stress range S-N", "weld_fatigue"),
    ("bolt fatigue preload cyclic", "bolt_fatigue"),
]

# Easy queries — clean paraphrases
EASY = [
    ("what is the anchorage length for passive reinforcement", "anchorage"),
    ("how to calculate lap splice length", "lap_splice"),
    ("what is the nominal cover for reinforcement", "nominal_cover"),
    ("durability requirements for concrete structures", "durability"),
    ("how does a VFD soft start work", "vfd_soft_start"),
    ("what is direct on-line motor starting", "direct_on_line"),
    ("design of shear links in concrete beams", "shear_links"),
    ("torsion reinforcement design requirements", "torsion_links"),
    ("what is creep of concrete", "creep"),
    ("what causes shrinkage in concrete", "shrinkage"),
    ("fatigue life of welded joints", "weld_fatigue"),
    ("bolt fatigue under cyclic loading", "bolt_fatigue"),
]


# ---------- helpers ----------

def build_bibliotheca(root: Path) -> Path:
    """Build a fresh bibliotheca with all corpus docs."""
    all_docs = {**CORPUS, **DISTRACTORS}
    con = db.connect(root)
    for doc_name, (filename, body) in all_docs.items():
        folder = root / doc_name
        folder.mkdir(exist_ok=True)
        (folder / filename).write_text(
            f"---\ndoc: {doc_name}\nsection: main\n---\n\n{body}\n",
            encoding="utf-8")
        chunks = embed.doc_chunks(folder)
        db.replace_document(con, doc_name, chunks,
                            embed.vectorize([c["text"] for c in chunks]))
    con.close()
    return root


def warm_up(bib: Path, record_appearances: bool) -> None:
    """Simulate a working session: search + hit on each gold topic."""
    for query, gold_topic in REASK:
        search(query, output=bib, top=5,
               record_appearances=record_appearances)
        con = db.connect(bib)
        try:
            row = con.execute(
                "SELECT id FROM chunks WHERE doc = ? LIMIT 1",
                (gold_topic,)).fetchone()
            if row:
                vec_f16 = np.asarray(
                    embed.vectorize_query(query), dtype="float16").tobytes()
                for _ in range(3):
                    session = db.increment_session(con)
                    db.record_access(con, row["id"], vec_f16,
                                     weight=5, session_id=session)
        finally:
            con.close()


def report_calibration(bib: Path) -> None:
    """Median top frecency score across gold chunks — feeds the Task 6 SCALE calibration.

    For each REASK query, re-embed it and ask db.ranked_by_frecency for the gold
    doc's own chunks; take the top score per gold chunk, print the median.
    """
    con = db.connect(bib)
    scores: list[float] = []
    try:
        for query, gold_topic in REASK:
            vec = embed.vectorize_query(query)
            ranked = db.ranked_by_frecency(con, vec, 20, doc=gold_topic)
            if ranked:
                scores.append(ranked[0][1])
    finally:
        con.close()
    if scores:
        print(f"  median warm-up frecency score: {float(np.median(scores)):.4f}")
    else:
        print("  median warm-up frecency score: n/a (no frecency state)")


def evaluate(bib: Path, queries: list[tuple[str, str]],
             fusion_mode: str, top: int = 5
             ) -> dict:
    """Run queries and compute metrics."""
    ranks = []
    for query, gold_topic in queries:
        results = search(query, output=bib, top=top,
                         fusion_mode=fusion_mode, no_frecency=False,
                         record_appearances=False)
        rank = None
        for i, r in enumerate(results, 1):
            if r["doc"] == gold_topic:
                rank = i
                break
        ranks.append(rank)

    n = len(queries)
    recall_1 = sum(1 for r in ranks if r == 1) / n
    recall_3 = sum(1 for r in ranks if r is not None and r <= 3) / n
    mrr = sum(1 / r for r in ranks if r is not None) / n
    return {"recall@1": round(recall_1, 3),
            "recall@3": round(recall_3, 3),
            "MRR": round(mrr, 3),
            "ranks": ranks}


def count_regressions(baseline_ranks: list, candidate_ranks: list) -> int:
    """Count queries where candidate is worse than baseline."""
    count = 0
    for b, c in zip(baseline_ranks, candidate_ranks):
        if b is not None and (c is None or c > b):
            count += 1
    return count


# ---------- main ----------

CONFIGS = [
    ("flat + hits_only",      "flat",     False),
    ("weighted + hits_only",  "weighted", False),
    ("bonus + hits_only",     "bonus",    False),
    ("flat + hits+appear",    "flat",     True),
    ("weighted + hits+appear","weighted", True),
    ("bonus + hits+appear",   "bonus",    True),
]


def main():
    import shutil
    import tempfile

    print("Building corpus and embedding (one-time cost)...")
    base_dir = Path(tempfile.mkdtemp(prefix="frecency_bench_"))
    corpus_dir = base_dir / "corpus"
    corpus_dir.mkdir()
    build_bibliotheca(corpus_dir)
    print(f"Corpus built at {corpus_dir}")

    all_results = {}

    for config_name, fusion_mode, record_app in CONFIGS:
        print(f"\n{'='*60}")
        print(f"Config: {config_name}")
        print(f"{'='*60}")

        # Fresh copy of the bibliotheca for each config
        run_dir = base_dir / config_name.replace(" ", "_").replace("+", "_")
        shutil.copytree(corpus_dir, run_dir)

        # Warm up
        print("  Warming up...")
        warm_up(run_dir, record_appearances=record_app)
        report_calibration(run_dir)

        # Evaluate
        results = {}
        for name, queries in [("adversarial", ADVERSARIAL),
                              ("reask", REASK), ("easy", EASY)]:
            print(f"  Evaluating {name}...")
            results[name] = evaluate(run_dir, queries, fusion_mode)

        all_results[config_name] = results

    # Report
    print(f"\n\n{'='*60}")
    print("RESULTS")
    print(f"{'='*60}\n")

    baseline_name = "flat + hits+appear"
    baseline = all_results[baseline_name]

    header = f"| {'config':<28} | {'R@1':>5} | {'R@3':>5} | {'MRR':>5} | {'regr':>4} |"
    separator = f"|{'-'*30}|{'-'*7}|{'-'*7}|{'-'*7}|{'-'*6}|"

    for qset in ["adversarial", "reask", "easy"]:
        print(f"\n### {qset} queries\n")
        print(header)
        print(separator)
        for config_name, _, _ in CONFIGS:
            r = all_results[config_name][qset]
            if config_name == baseline_name:
                regr = "(base)"
            else:
                regr = str(count_regressions(
                    baseline[qset]["ranks"], r["ranks"]))
            print(f"| {config_name:<28} | {r['recall@1']:>5} | "
                  f"{r['recall@3']:>5} | {r['MRR']:>5} | {regr:>4} |")

    # Pick winner: highest average MRR across all sets, zero regressions preferred
    best_name = None
    best_avg_mrr = -1
    for config_name, _, _ in CONFIGS:
        r = all_results[config_name]
        avg_mrr = sum(r[q]["MRR"] for q in ["adversarial", "reask", "easy"]) / 3
        total_regr = sum(
            count_regressions(baseline[q]["ranks"], r[q]["ranks"])
            for q in ["adversarial", "reask", "easy"]
        ) if config_name != baseline_name else 0
        if avg_mrr > best_avg_mrr or (avg_mrr == best_avg_mrr and total_regr == 0):
            best_avg_mrr = avg_mrr
            best_name = config_name

    print(f"\nWinner: {best_name} (avg MRR: {best_avg_mrr:.3f})")

    # Cleanup
    print(f"\nBenchmark data at: {base_dir}")
    print("Delete manually when done: shutil.rmtree(path)")


if __name__ == "__main__":
    main()
