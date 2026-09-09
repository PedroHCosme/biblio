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

---

## 7. Tuning benchmark — first corpus (2026-09-09), superseded by §8

First committed version of `scripts/benchmark/04_frecency.py` used a 12-topic
corpus where each topic had exactly one matching document. Result: **cold
retrieval already scored 1.0 / 1.0 / 1.0 on the re-ask and easy sets** — no
headroom, so frecency could not show a gain there and the whole comparison
rested on 24 adversarial queries with ~1-query deltas. `bonus + hits_only` won
by +0.019 MRR; `weighted` was byte-identical to `flat`; `hits_only` beat
`hits+appear` by a hair. The direction was right but the corpus was too easy to
prove anything. Replaced — see §8.

---

## 8. Tuning benchmark — headroom corpus (2026-09-09)

`scripts/benchmark/04_frecency.py` rebuilt so cold retrieval genuinely fails.

**Corpus:** 6 topic clusters × 3 **near-duplicate sibling documents** + 6
distractors (24 docs). Within a cluster the three siblings share ~70 % of their
wording and differ on one axis only — e.g. *anchorage length* as
Eurocode 2 / ACI 318 / fib Model Code; *concrete cover* for
chloride / carbonation / fire; *reduced-voltage motor start* by
VFD / star-delta / autotransformer. Vector + FTS cannot reliably order the
siblings.

**Gold = one specific sibling per query** — the one a simulated work session
searched for and `biblio hit` 3× (weight 5). Three query sets, 6 queries each
(one per cluster):

| set | query is… | cold R@1 | cold MRR |
|---|---|---|---|
| **reask** | the exact phrase the session used | 0.33 | 0.56 |
| **easy** | a plain-language paraphrase of the same need | 0.00 | 0.39 |
| **cross** | phrased in a *neighbouring* sibling's vocabulary | 0.00 | 0.35 |

Cold `no_frecency=True` is now a real reference point, not a ceiling. Runs are
fully deterministic (no RNG; identical across repeats).

### Full matrix (recall@1 / recall@3 / MRR; `regr` = queries ranked worse than cold)

**reask (n=6)**

| row | R@1 | R@3 | MRR | regr |
|---|---|---|---|---|
| COLD (no frecency)      | 0.33 | 1.0 | 0.56 | — |
| flat + hits_only        | 1.00 | 1.0 | 1.00 | 0 |
| weighted + hits_only    | 1.00 | 1.0 | 1.00 | 0 |
| **bonus + hits_only**   | 1.00 | 1.0 | 1.00 | 0 |
| flat + hits+appear      | 0.83 | 1.0 | 0.92 | 0 |
| weighted + hits+appear  | 1.00 | 1.0 | 1.00 | 0 |
| bonus + hits+appear     | 0.67 | 1.0 | 0.81 | 0 |

**easy (n=6)**

| row | R@1 | R@3 | MRR | regr |
|---|---|---|---|---|
| COLD (no frecency)      | 0.00 | 1.0 | 0.39 | — |
| flat + hits_only        | 0.83 | 1.0 | 0.92 | 0 |
| weighted + hits_only    | 0.83 | 1.0 | 0.92 | 0 |
| **bonus + hits_only**   | 1.00 | 1.0 | 1.00 | 0 |
| flat + hits+appear      | 0.83 | 1.0 | 0.89 | 0 |
| weighted + hits+appear  | 1.00 | 1.0 | 1.00 | 0 |
| bonus + hits+appear     | 0.50 | 1.0 | 0.69 | 0 |

**cross (n=6)**

| row | R@1 | R@3 | MRR | regr |
|---|---|---|---|---|
| COLD (no frecency)      | 0.00 | 0.67 | 0.35 | — |
| flat + hits_only        | 0.83 | 1.0  | 0.92 | 0 |
| weighted + hits_only    | 0.83 | 1.0  | 0.92 | 0 |
| **bonus + hits_only**   | 0.83 | 1.0  | 0.92 | 0 |
| flat + hits+appear      | 0.33 | 1.0  | 0.61 | 0 |
| weighted + hits+appear  | 0.50 | 1.0  | 0.69 | 0 |
| bonus + hits+appear     | 0.33 | 0.83 | 0.57 | 0 |

**summary — avg MRR over the 3 sets**

| row | avg MRR | Δ vs cold |
|---|---|---|
| COLD (no frecency)      | 0.433 | — |
| flat + hits_only        | 0.945 | +0.512 |
| weighted + hits_only    | 0.945 | +0.512 |
| **bonus + hits_only**   | **0.972** | **+0.540** |
| flat + hits+appear      | 0.806 | +0.373 |
| weighted + hits+appear  | 0.898 | +0.465 |
| bonus + hits+appear     | 0.690 | +0.257 |

Calibration — median warm-up frecency score: **6.56** (hits_only), **6.68**
(hits+appear); both ≫ `BONUS_SCALE` = 1.0, so `min(score/BONUS_SCALE, MAX_BONUS)`
saturates at `MAX_BONUS` for every warmed sibling.

### Reading it — and whether the §7 deletions were right

- **Frecency is now a large, safe win.** +0.51–0.54 MRR over cold, cold R@1
  0.0–0.33 → warm 0.83–1.0, **zero regressions** in any of the 18 config×set
  cells. The MVP concern ("re-ask shows no movement") was a corpus artifact — on
  a corpus where cold actually struggles, re-ask goes 0.56 → 1.00 MRR.

- **Deleting `hits+appear` — confirmed, and it's not marginal.** On this corpus
  the weight-1 "it appeared in a search" records are *actively harmful*:
  `flat` drops 0.945 → 0.806, `bonus` drops 0.972 → **0.690**. During warm-up
  every search writes its whole top-5 as weight-1 accesses, so the *wrong*
  siblings accumulate frecency too; with near-identical siblings that pollution
  swamps the weight-5 hit. `hits_only` keeps the signal clean.

- **Deleting `weighted` — confirmed.** In the `hits_only` regime we actually
  ship, `weighted` is byte-identical to `flat` again (0.945 = 0.945, every cell).
  It only ever helped in the `hits+appear` regime (0.806 → 0.898) — i.e. it
  partly *compensates* for the noise that `hits_only` removes at the source.
  Once you drop `hits+appear`, `weighted` has nothing left to do.

- **Shipping `bonus` — confirmed.** Best mode: ties `flat`/`weighted` on reask
  and cross, and fixes one more query to rank-1 on easy (0.83 → 1.00), for the
  top avg MRR (0.972) with zero regressions.

- **recall@3 is near-ceiling cold** (1.0 on reask/easy, 0.67 on cross): the
  siblings *are* all retrieved, they're just mis-ordered. Frecency's whole job
  here is to reorder the retrieved siblings so the one you use lands at #1 —
  which is exactly what the recall@1 column shows it doing.

### Decision — shipped

**`bonus` fusion + `hits_only` recording** is the only behaviour now. The
`flat` / `weighted` fusion paths and the weight-1 appearance recording are
deleted; the `fusion_mode` and `record_appearances` parameters are gone;
`BASE_WEIGHT` / `FRECENCY_SCALE` dropped, `MAX_BONUS` / `BONUS_SCALE` kept.
`save_last_query_vec` still runs on every non-`--no-frecency` search — `biblio
hit` depends on it.

`scripts/benchmark/04_frecency.py` carries a frozen local copy of all three
fusion strategies (`_rank()`) plus the appearance-recording, so it still runs
the full 6-config comparison after the production paths are gone. It reproduces
every cell of the table above exactly — the reimplementation is faithful.

### Caveats

- 6 queries per set. Deltas are large (cold 0.35–0.56 → warm 0.92–1.0) so the
  direction is not in doubt, but exact MRR values shouldn't be over-read.
- Synthetic near-duplicate siblings are an idealised version of the real case
  (same topic across editions / standards / vendors in one library). Real
  corpora are messier and the cold baseline would usually be a little better.

---

## 9. Memory / cost of the `accesses` table, and the candidate-scoping fix

Measured on real SQLite DBs (not estimated).

### What a record costs

Each `accesses` row stores the full query vector as fp16 (`DIM` = 384 → 768 B)
plus `chunk_id` / `weight` / `session_id`. **Measured 830 B/row** including the
`idx_accesses_chunk` entry and SQLite overhead. Hard cap 20 rows/chunk
(`ACCESS_CAP`); no global cap.

### Disk — worst case (every chunk hit, cap full)

| | per chunk |
|---|---|
| indexed content (fp32 vector + text + FTS) | ~5.8 KB |
| frecency at 20 accesses | ~16.6 KB |
| **ratio** | **frecency ≈ 2.85× the content, 74% of the file** |

Extrapolated: 1 book (~600 ch) +10 MB · 20-book library (~12k ch) +200 MB ·
100k ch +1.6 GB. Realistic heavy use (a few thousand distinct sections ever
hit) → tens of MB. `hits+appear` would have reached the bad regime far faster
(every search wrote its whole top-5) — another point for dropping it.

### Latency — the real problem, now fixed

`ranked_by_frecency` runs on every non-`--no-frecency` search. **Before this
change it scanned every chunk ever accessed in the whole DB**, Python-looping a
per-row fp16→fp32 dot product:

| access rows in DB | old: added to every search |
|---|---|
| 4,000 | +80 ms |
| 20,000 | +450 ms |
| 100,000 | +1,480 ms |

It grew monotonically with cumulative distinct sections hit — never corpus
size, never recency, never shrinking. Search is ~100 ms warm, so a power user
who had hit ~1,000 sections was paying 5× latency.

**Fix (shipped):** `ranked_by_frecency` now takes the caller's candidate set
(the vector + FTS hits, ~40 chunks) and scores only those —
`WHERE chunk_id IN (…)`. This matches how the signal is actually used: `bonus`
mode only re-ranks already-retrieved chunks, so scoring the rest of history was
pure waste.

| access rows in DB | new: added to every search |
|---|---|
| 20,000 | ~8 ms |
| 100,000 | ~6 ms |
| 400,000 | ~6 ms |

**Flat, ~6 ms, independent of history size.** The 6-config benchmark is
byte-identical before and after the change (with 24 docs every doc is always a
candidate, so scoping is a behavioural no-op there) — confirming it only removes
cost, not signal.

Behaviour note: `flat` / `weighted` can no longer surface a frecency-only chunk
that vector + FTS both missed. Irrelevant for the shipped `bonus` mode (never
could), and those two modes are being deleted anyway.

### Not done (available if disk ever matters)

- Store the vector as int8 (halves the row to ~400 B) — skipped: adds
  quantisation noise to the `SIMILARITY_THRESHOLD` / `PRUNE_THRESHOLD` maths for
  a disk saving that is no longer on any critical path.
- Real expiry: a record dissimilar to every future query is currently immortal
  (pruning only fires when a *similar* query finds its contribution < 0.01). A
  flat "drop anything older than N sessions" would bound disk regardless of
  query patterns. Cheap, but not urgent now that read cost is O(candidates).
- Vectorise `frecency_score` (one matmul instead of the per-row loop) — ~6 ms →
  ~0.5 ms. Not worth it against a 100 ms search.
