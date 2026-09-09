# Frecency ranking — benchmark results and two tuning knobs

Date: 2026-09-08
Branch: `worktree-frecency-ranking` (commits `41e2ff2`, `aff04d6`, `7fd02f9`)
Status: feature works and is safe to ship; this doc argues it is under-tuned and
proposes two cheap changes.

---

## 1. What was measured

No committed benchmark script yet (lives in the session scratchpad,
`bench_frecency.py` + `agg.py`). It runs the **real** search path with **real**
embeddings against a synthetic corpus.

**Corpus:** 12 short documents in 6 deliberately confusable topic pairs
(`anchorage`/`lap_splice`, `nominal_cover`/`durability`,
`vfd_soft_start`/`direct_on_line`, `shear_links`/`torsion_links`,
`creep`/`shrinkage`, `weld_fatigue`/`bolt_fatigue`) plus 8 unrelated distractor
docs. Pairs share vocabulary on purpose, so semantic + FTS alone frequently rank
the sibling first.

**Cold:** `search(query, no_frecency=True)` — semantic + FTS5 only.

**Warm:** one simulated session first — for each topic, one clean-phrasing
search + `biblio hit` on the gold section 3× (weight 5) — then
`search(query)` with frecency on.

**Queries:** held-out, worded in the *sibling's* vocabulary (24 queries, 2 per
topic). Plus a separate **re-ask** set: the exact phrasings the agent already
hit during the warm-up session.

Metrics: recall@1, recall@3, MRR, per-query rank delta.

---

## 2. Headline numbers

### Held-out adversarial queries (24 queries)

| metric   | cold  | warm  | Δ       |
|----------|-------|-------|---------|
| recall@1 | 0.583 | 0.583 | 0       |
| recall@3 | 0.875 | 0.958 | +0.083  |
| MRR      | 0.749 | 0.767 | +0.018  |

Per-query: **5 improved, 18 unchanged, 1 regressed.** Mean rank delta **+0.21**.
Of the 10 queries not already rank-1 cold, 5 improved (50%).

Rank changes:

| topic          | cold → warm | note        |
|----------------|-------------|-------------|
| nominal_cover  | 5 → 4       | improved    |
| nominal_cover  | 3 → 2       | improved    |
| durability     | 5 → 3       | improved    |
| torsion_links  | 2 → 1       | improved    |
| bolt_fatigue   | 4 → 3       | improved    |
| shear_links    | 1 → 2       | **regressed** |

### Re-ask queries (same phrasing the agent hit during warm-up)

| metric   | cold  | warm  | Δ |
|----------|-------|-------|---|
| recall@1 | 0.75  | 0.75  | 0 |
| recall@3 | 1.0   | 1.0   | 0 |
| MRR      | 0.861 | 0.861 | 0 |

**Zero movement.** This is the scenario frecency exists for.

### Easy corpus (clean paraphrases, no adversarial wording)

recall@1 0.875 → 0.875, recall@3 0.958 → 1.0, MRR 0.927 → 0.931. Baseline is
already near ceiling; only 1 query moves.

---

## 3. Reading the results

**Net positive, small.** Frecency never makes aggregate retrieval worse. On hard
ambiguous queries it recovers a gold section buried at rank 2–4 by roughly one
position, and it reliably pushes *unrelated* distractors out of the top 5.

Example — query `"distance from surface to bar for the exposure class"`:

```
cold : anchorage · deflection-limits · [nominal-cover] · harmonic-distortion · durability
warm : anchorage · [nominal-cover]   · durability     · lap-splice          · torsion-links
```

Gold moved 3 → 2 and both unrelated distractors dropped out of the top 5. That
denoising is the consistent, defensible effect.

**Two things it does not do:**

1. **It never fixes rank-1.** recall@1 is flat on every set. When a completely
   different wrong document dominates the top spot, one extra RRF vote cannot
   dislodge it.
2. **Re-ask shows no gain at all** — and re-ask is the primary use case.

### Why re-ask is inert

Two compounding structural reasons:

1. **Decay outruns the session cadence.** A "session" bumps on every single
   search (`db.increment_session` is called once per `search()`). By the time
   the re-ask measurement ran, the session counter was ~48; the hits were
   recorded at sessions 1–12. `decay = 2^(-age/half_life)` with `half_life = 7`
   gives `2^(-~40/7) ≈ 0.02` — the frecency contribution had almost entirely
   decayed *within the same sitting*. A busy agent burns through the half-life
   in one afternoon.

2. **RRF flattens magnitude.** Frecency enters fusion as one more ranked list.
   Its contribution to a chunk's score is `1/(K_RRF + position)` regardless of
   whether the underlying frecency score is 0.02 or 20. A confident frecency
   signal and a nearly-decayed one cast an identical vote. So frecency can only
   ever move a result by ~1 rank, and only when the base rankings already put it
   close.

The `shear_links` regression is the same mechanism in reverse: frecency gave a
confusable sibling one vote and nudged a query that was already correct down to
rank 2.

---

## 4. Two cheap knobs to make it earn its place

Both are small, local, and independently testable.

### Knob A — count real sessions, not searches

**Problem:** `increment_session` fires once per `search()` call, so "age in
sessions" is really "age in searches". Half-life 7 means the signal is
half-dead after 7 queries.

**Change:** bump the session counter only on a *new* sitting — process start, or
the first search after a wall-clock gap (e.g. > 30 min since the last recorded
access). Store `last_access_time` in `config`; in `search.py`, call
`increment_session` only when the gap exceeds the threshold, otherwise reuse the
current session id.

**Cost:** ~5 lines. One config row, one timestamp comparison at the top of the
per-bibliotheca block in `search.py`. `record_access` and `frecency_score` are
unchanged — they already take `session_id` as a parameter.

**Effect:** a hit stays fresh across a realistic working session instead of
decaying inside it. Re-ask within the same day would actually carry weight.

**Open question for analysis:** wall-clock gap vs. an explicit session marker
(e.g. biblio learns the agent's session id from an env var the skill sets). Gap
is zero-config but fuzzy; explicit is precise but needs the skill to cooperate.

### Knob B — let frecency cast a weighted vote

**Problem:** RRF treats frecency as a binary "this chunk is in the list at
position N". The actual score magnitude is discarded.

**Change:** in `search.py`, where the frecency ranked list is folded into RRF,
scale its per-chunk contribution by a saturating function of the frecency score:

```python
# instead of the flat 1/(K_RRF + pos) that every other list gets:
boost = frecency_weight * (1 - exp(-score / scale))   # saturates in [0, frecency_weight]
fused[chunk_id] += boost / (K_RRF + pos)
```

`frecency_weight` (start at 1.0) and `scale` (start near the median observed
score) are the two tunables. A strong, recent hit gets close to a full vote; a
nearly-decayed one gets almost nothing — which also removes most of the
regression risk, since a weak frecency signal can no longer nudge a correct
result off the top.

**Cost:** ~3 lines in the fusion loop, plus the two constants next to the
existing `K_RRF`, `HALF_LIFE`, etc. in `db.py`.

**Effect:** frecency stops being able to demote a confidently-ranked result on a
thin signal, and a confident signal can push harder than one rank when it
deserves to.

**Open question for analysis:** whether B alone is enough (a confident signal
can still only add < 1 extra RRF unit, so it still won't beat a dominant wrong
doc), or whether frecency should short-circuit fusion entirely above some score
threshold ("the agent explicitly hit this for this query — put it first").

---

## 5. Recommendation

Ship the feature as-is (it is safe and cheap), then evaluate A and B against a
committed version of this benchmark. Suggested: add
`scripts/benchmark/04_frecency.py` — the existing scripts in that folder are
stale (old Portuguese API) so nothing there needs touching.

Priority order for analysis: **A first** (the decay/cadence mismatch is the
bigger problem and the fix is unambiguous), then **B** (needs tuning and a
decision on the fusion-vs-short-circuit question).

---

## 6. Caveats

- Synthetic corpus, no real-acervo run: `robotics` and `conversores` predate the
  PT→EN rename (`04de3d8`) and current biblio cannot open them without a full
  reingest.
- The synthetic bench understates the real-world win: an agent returning to the
  same corpus across *many* days, compounding hits on the sections that matter.
  It also can't see the cost of a wrong frecency boost persisting for weeks —
  which is exactly what Knob A changes.
- n = 24 held-out queries. A recall@3 delta of +0.083 is 2 queries. Treat the
  direction as signal, not the magnitude.
