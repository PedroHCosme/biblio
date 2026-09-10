# biblio Robustness Fixes

**Date:** 2026-09-10
**Status:** Approved
**Scope:** Four independent fixes to biblio's operational edges — library registration/visibility, offline search startup, `biblio update` on Windows, and ingest throughput/safety — plus the skill guidance that mirrors the new ingest knobs to Claude.

## Origin

Field report from a real session using biblio against `aig-docs`:

1. A fresh Claude session answered "aignosi branch naming convention" from general knowledge instead of biblio — `aig-docs` was never visible to it.
2. `biblio search` was slow every call and warned about "unauthenticated requests to HF Hub".
3. `biblio update` failed with `WinError 32`.
4. Ingesting the `aig-docs` folder was estimated at multiple days; a single 48 MB slide deck sat in OCR for 1h30.

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Spec shape | One spec, four tracks | Fixes are small and share the "biblio's edges are unreliable" theme; split at plan time only if needed |
| A — when to register a bibliotheca | Before the ingest loop, not after | An interrupted or multi-day run must not leave the lib orphaned |
| A — `MAX_NAMES` cap | 8 → 20 | Real setups never hit 20; early-register is the actual fix, cap is secondary safety |
| B — HF Hub offline | Force `HF_HUB_OFFLINE=1` + `HF_HUB_DISABLE_TELEMETRY=1`, auto-recover on cache miss | Model is already cached; the Hub call is pure overhead. First-run download must still work |
| C — `biblio update` on Windows | Print the manual `pip install` command and exit | Windows can't replace the running `.exe`; a detached respawn is fragile. POSIX keeps auto-update |
| D — OCR ceiling | `--max-ocr-pages N`, default 25 (~12 min/file at ~30s/page) | Per-page routing is sound; what's missing is a per-file ceiling with a human decision point |
| D — long-run visibility | `--dry-run` on `biblio add`: triage whole folder, print estimate, write nothing | One deliberate decision point before any wait |
| D — non-interactive over-cap behavior | Skip flagged files, list them at end with remediation line | Unattended runs must never silently take hours |
| D — summaries | Keep `auto` mode but confirm once per run when Ollama is detected and no flag given; default no | `auto` silently auto-summarizing every doc contradicts SKILL.md's "opt-in"; a one-time prompt keeps the convenience without the surprise |
| A′ — skill guidance | Add an "Ingesting a folder" section teaching Claude to `--dry-run` first and put the flag choices to the user | A user asking Claude to build a bibliotheca should get the same control a CLI user has with flags |

## Track A — Library visibility

**Problem.** `register()` is called once, *after* the ingest loop completes
([`biblio/pipeline.py:158`](../../../biblio/pipeline.py)). A run that is interrupted or
still in progress (the `aig-docs` run was estimated in days) never registers the
bibliotheca, so `biblio libs` and the generated skill description never mention it —
and a fresh Claude session has no signal that the corpus exists. Compounding it,
`biblio skill` builds the description from `known_bibliothecas()[:MAX_NAMES]` with
`MAX_NAMES = 8` ([`biblio/skill.py:13`](../../../biblio/skill.py)) and silently drops
entries past the 8th.

**Change.**
- In `ingest()` ([`biblio/pipeline.py`](../../../biblio/pipeline.py)): move
  `register(bibliotheca)` from after the loop to immediately after
  `bibliotheca.mkdir(parents=True, exist_ok=True)`, before the first file is
  processed. Remove the trailing `if count["ok"] or count["skipped"]: register(...)`
  block. `register()` is idempotent (moves the path to the top of the registry).
- `biblio/skill.py`: `MAX_NAMES = 8` → `MAX_NAMES = 20`.

**Out of scope.** Auto-pruning stale registry entries — `known_bibliothecas()`
already filters paths that no longer exist on disk, and a 20-name cap makes the
benchmark-entry pollution moot.

## Track B — Instant search

**Problem.** Each `biblio search` process imports `sentence_transformers`, which
contacts the HF Hub to revalidate the cached model (etag check) and prints
`Warning: You are sending unauthenticated requests to the HF Hub`. The network
round-trip is subject to rate-limiting and adds seconds to every call. The model
(`paraphrase-multilingual-MiniLM-L12-v2`) is already in the local cache; the
benchmark scripts already set `HF_HUB_OFFLINE=1` but the CLI does not.

**Change.** In [`biblio/embed.py`](../../../biblio/embed.py), before any
`sentence_transformers` import (module top level):

```python
import os
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
```

In `_model()`, wrap the `SentenceTransformer(MODEL)` construction: if it raises
(model not in cache — genuine first run), clear `HF_HUB_OFFLINE` from the
environment, retry once, then restore the previous value. On success the retry
path is never taken, so steady-state cost is zero.

`setdefault` means an operator who explicitly exports `HF_HUB_OFFLINE=0` can still
force online behavior.

## Track C — `biblio update` on Windows

**Problem.** `biblio update` runs
`pip install --upgrade git+https://github.com/PedroHCosme/biblio.git` via
`subprocess.run([sys.executable, "-m", "pip", ...])`
([`biblio/cli.py:197`](../../../biblio/cli.py)). pip's uninstall step tries to
replace `Scripts/biblio.exe`, which is the running process image; Windows denies
it with `WinError 32` (sharing violation).

**Change.** In the `update` branch of `cli.py`: when `sys.platform == "win32"`,
print the exact command and return 0 without running it:

```
biblio can't update itself on Windows (the running .exe is locked).
Run this in a fresh shell:

  <sys.executable> -m pip install --upgrade git+https://github.com/PedroHCosme/biblio.git
```

Non-Windows platforms keep the current behavior unchanged.

## Track D — Ingest throughput & safety

### D.1 Context: the OCR routing is correct, the ceiling is missing

`triage()` ([`biblio/triage.py`](../../../biblio/triage.py)) routes **per page**:
a page with `< 120` chars of extractable text → `ocr` (docling with OCR, ~30 s/page
on CPU); a page with text and a table → `complex` (docling, no OCR); otherwise →
`native` (`pymupdf4llm`, ~free). A born-digital PDF therefore costs almost nothing.
The pathological case is an image-only slide deck: ~every page is `< 120` chars, so
all pages route to OCR through a one-page-PDF-per-page docling pipeline, with no
upper bound and no confirmation. `triage()` already computes the OCR page count and
even prints `~{n_ocr * 30}s` — it just never acts on it.

The per-page routing stays. Two things get added: a per-file ceiling and an
upfront estimate.

### D.2 `--dry-run` on `biblio add`

New flag on the `add` subparser. When set: run `triage()` over every file in the
target folder, print the breakdown below, write nothing, exit 0.

```
biblio add <folder> --dry-run

  624 documents  (593 .md, 31 .pdf)
  OCR pages total: 412  (~206 min on CPU)

  Over --max-ocr-pages (25):
    18122025-hydro-pt-v3-sientia-saas          238 OCR pages  (~119 min)
    16072026-presales-deck-cases-en             94 OCR pages  (~47 min)

  Proceed: biblio add <folder>                 # prompts about the 2 files above
           biblio add <folder> --yes           # skips them, indexes the rest
           biblio add <folder> --max-ocr-pages 0   # OCR everything, no cap
```

Reuses the existing triage code path; the only new work is aggregation and
formatting.

### D.3 `--max-ocr-pages N` (default 25)

New flag on the `add` subparser, `type=int`, `default=25`. `0` disables the cap.

During a folder `add`, after triaging each file, if its OCR page count `> N` the
file is **held back**:

- **Interactive TTY:** after triaging the whole folder, one prompt —
  `N files exceed the OCR cap (~M min total). [p]roceed with all / [s]kip them / [a]bort?`
  Default `s`.
- **`--yes` or no TTY:** skip the flagged files. At the end of the run, list them:
  ```
  skipped (over OCR budget, 25 pages):
    18122025-hydro-pt-v3-sientia-saas  — run: biblio add <file> --fast   (or --max-ocr-pages 0)
  ```

`--max-size` (MB) and `--fast` are unchanged and compose with this.

### D.4 Summaries — confirm once

`wants_summary("auto", ...)` currently returns `True` whenever Ollama + the qwen
model are already present ([`biblio/ollama.py:48`](../../../biblio/ollama.py)), so
`biblio add` silently summarizes every document (~75–180 s each on CPU) for anyone
who once ran `--summary`. SKILL.md says summaries are opt-in.

**Change.** In the `auto` branch of `wants_summary()`: when `available()` and
`_has_model()` are both true and the mode is `auto` (no explicit `--summary` /
`--no-summary`), ask once via the `ask` callback —
`"Ollama detected — generate per-document summaries (~<n>s each)? [y/N]"`, default
**no**. `--summary` and `--no-summary` bypass the prompt entirely.
`biblio index --summary` remains the backfill path.

When `ask` is `None` (non-interactive / GUI), `auto` resolves to **no**.

### D.5 Cost of the folder-wide triage pass

`--dry-run` and the `--max-ocr-pages` gate both need `triage()` run over the whole
folder before any conversion. For a ~600-file corpus this is a pymupdf `open` +
`find_tables()` per page — roughly 1–2 minutes. Acceptable: it is the price of a
real estimate, and `--dry-run` makes it an explicit, separate step.

## Track A′ — Teach Claude the same knobs

The `bibliotheca` SKILL.md ("Other commands" table) documents only a subset of
`add`'s behavior. Add a short **"Ingesting a folder"** subsection to `PROTOCOL` in
[`biblio/skill.py`](../../../biblio/skill.py):

- Run `biblio add <folder> --dry-run` first and show the user the estimate.
- If any file is flagged over the OCR cap, put the choice to the user
  (`--fast` that file, raise `--max-ocr-pages`, or skip it) — do not pass `--yes`
  past the cap without their OK.
- Summaries: still ask before `--summary` (unchanged guidance), and mention that a
  plain `add` will prompt once if Ollama is installed.

The generated `CLAUDE.md` (for copied bibliothecas) gets the same subsection via
the shared `PROTOCOL` string.

## Files touched

| File | Tracks |
|---|---|
| `biblio/pipeline.py` | A (register early) |
| `biblio/skill.py` | A (`MAX_NAMES`), A′ (protocol text) |
| `biblio/embed.py` | B |
| `biblio/cli.py` | C, D.2, D.3 (argparse + wiring) |
| `biblio/ollama.py` | D.4 |
| `biblio/triage.py` or a new aggregation helper | D.2, D.3 (folder-wide OCR count) |
| `tests/` | one test per track (see below) |

## Testing

- **A:** `ingest()` on a fresh folder registers the bibliotheca before processing —
  assert the registry contains the path even if a mid-loop exception is raised.
- **A:** `skill._description()` includes the 9th–20th bibliotheca names.
- **B:** importing `biblio.embed` sets `HF_HUB_OFFLINE`; `_model()` retries online
  once when the offline load raises (monkeypatch `SentenceTransformer`).
- **C:** `main(["update"])` on `win32` (monkeypatch `sys.platform`) prints the
  command and does not call `subprocess.run`.
- **D.2:** `biblio add --dry-run` on a fixture folder prints the OCR total and the
  over-cap file list, and creates no bibliotheca directory.
- **D.3:** folder `add` with `--yes` and a fixture PDF over the cap skips that file,
  processes the rest, and the skipped file appears in the final report.
- **D.4:** `wants_summary("auto", ask=<stub returning False>)` returns `False` even
  when `available()` and `_has_model()` are stubbed `True`; returns `True` when the
  stub returns `True`; `wants_summary("auto", ask=None)` returns `False`.

## Non-goals

- A persistent search daemon (the cold-start import cost beyond the Hub call is out
  of scope; B removes the network portion only).
- Changing docling's one-page-PDF-per-page conversion strategy.
- Auto-`--fast` fallback for over-cap files (skip-and-report was chosen instead).
- Auto-pruning the bibliotheca registry.
- `biblio search` returning content — that is intentional and stays.
