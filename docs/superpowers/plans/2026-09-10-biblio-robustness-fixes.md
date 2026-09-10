# biblio Robustness Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix four operational edges in biblio — library visibility during long ingests, offline search startup, `biblio update` on Windows, and ingest throughput/safety — and mirror the new ingest knobs into the skill text.

**Architecture:** Small, independent changes across six modules. Track A moves an idempotent `register()` call earlier and lifts a cap. Track B sets two env vars before `sentence_transformers` loads, with a one-shot online fallback. Track C branches `biblio update` on `sys.platform`. Track D adds a pure `pipeline.survey()` triage-aggregation function, wires `--dry-run` / `--max-ocr-pages` / `--yes` into the `add` subparser, and makes `auto` summaries prompt once. Track A′ edits the shared `PROTOCOL` string.

**Tech Stack:** Python 3.11+, argparse, pytest, pymupdf, sentence-transformers, sqlite.

**Spec:** [`docs/superpowers/specs/2026-09-10-biblio-robustness-design.md`](../specs/2026-09-10-biblio-robustness-design.md)

---

## File Structure

| File | Change |
|---|---|
| [`biblio/pipeline.py`](../../../biblio/pipeline.py) | `register()` moves before the loop; `ingest()` gains `exclude` param + end-of-run skip report; new `survey()` function |
| [`biblio/skill.py`](../../../biblio/skill.py) | `MAX_NAMES` 8 → 20; new "Ingesting a folder" section in `PROTOCOL` |
| [`biblio/embed.py`](../../../biblio/embed.py) | `HF_HUB_OFFLINE` / `HF_HUB_DISABLE_TELEMETRY` at import; `_model()` online-retry fallback |
| [`biblio/cli.py`](../../../biblio/cli.py) | `add` subparser flags; `--dry-run` / over-cap orchestration; Windows branch in `update`; `_choose()` / `_print_survey()` / `_over_cap_exclude()` helpers |
| [`biblio/ollama.py`](../../../biblio/ollama.py) | `wants_summary()` `auto` branch prompts once |
| `tests/test_robustness.py` (new) | one or more tests per track |

`survey()` lives in `pipeline.py` (not `triage.py`) because it needs the private `_files()` walker; `triage.py` stays a pure per-PDF module.

`ingest()` gets only `exclude: frozenset[Path]` — the CLI owns the cap policy (survey → prompt → exclude set), so the GUI path is unaffected and no `max_ocr_pages` parameter threads through the pipeline.

---

## Task 1: Track A — register the bibliotheca before the ingest loop

**Files:**
- Modify: [`biblio/pipeline.py`](../../../biblio/pipeline.py) — `ingest()`, lines ~144–160
- Test: `tests/test_robustness.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_robustness.py
from pathlib import Path

from biblio import pipeline
from biblio.paths import known_bibliothecas


def _boom(*a, **k):
    raise RuntimeError("boom")


def test_registers_bibliotheca_before_processing(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "_process_one", _boom)
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.md").write_text("# x\n" + "y " * 40, encoding="utf-8")
    out = tmp_path / "lib"

    pipeline.ingest(src, output=out)  # every file fails, loop swallows it

    assert str(out.resolve()) in known_bibliothecas()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/c/Users/Usuario/.conda/envs/alcoa/python.exe -m pytest tests/test_robustness.py::test_registers_bibliotheca_before_processing -v`
Expected: FAIL — registry empty because the trailing `register()` block only runs when `count["ok"] or count["skipped"]`, and here everything failed.

- [ ] **Step 3: Move `register()` up and delete the trailing block**

In `ingest()`, immediately after `bibliotheca.mkdir(parents=True, exist_ok=True)`:

```python
    bibliotheca = root(output)
    bibliotheca.mkdir(parents=True, exist_ok=True)
    register(bibliotheca)  # early: a multi-day or interrupted run must still be visible
    summarize_with_ollama = ollama.wants_summary(summary, ask, warn)
```

Delete the block at the end of the function:

```python
    if count["ok"] or count["skipped"]:
        register(bibliotheca)
```

(so the function now ends `return count`).

- [ ] **Step 4: Run test to verify it passes**

Run: `/c/Users/Usuario/.conda/envs/alcoa/python.exe -m pytest tests/test_robustness.py::test_registers_bibliotheca_before_processing tests/test_idempotency.py -v`
Expected: PASS (idempotency tests unaffected — `register()` writes the isolated test registry, not the bibliotheca folder).

- [ ] **Step 5: Commit**

```bash
rtk git add biblio/pipeline.py tests/test_robustness.py && rtk git commit -m "fix(pipeline): register bibliotheca before the ingest loop

An interrupted or multi-day run never reached the trailing register() call,
so biblio libs and the generated skill never mentioned the corpus. register()
is idempotent (moves the path to the top).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 2: Track A — raise `MAX_NAMES` to 20

**Files:**
- Modify: [`biblio/skill.py:13`](../../../biblio/skill.py) — `MAX_NAMES = 8`
- Test: `tests/test_robustness.py`

- [ ] **Step 1: Write the failing test**

```python
from biblio import skill


def test_description_lists_up_to_twenty_bibliothecas(monkeypatch):
    fake = [f"/x/lib{i:02d}" for i in range(25)]
    monkeypatch.setattr("biblio.skill.known_bibliothecas", lambda: fake)

    d = skill._description()

    assert "lib08" in d  # 9th entry — dropped under the old cap of 8
    assert "lib19" in d  # 20th entry
    assert "lib20" not in d  # 21st — still capped
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/c/Users/Usuario/.conda/envs/alcoa/python.exe -m pytest tests/test_robustness.py::test_description_lists_up_to_twenty_bibliothecas -v`
Expected: FAIL — `lib08` not in description (cap is 8).

- [ ] **Step 3: Change the constant**

[`biblio/skill.py:13`](../../../biblio/skill.py):

```python
MAX_NAMES = 20
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/c/Users/Usuario/.conda/envs/alcoa/python.exe -m pytest tests/test_robustness.py::test_description_lists_up_to_twenty_bibliothecas -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
rtk git add biblio/skill.py tests/test_robustness.py && rtk git commit -m "fix(skill): raise MAX_NAMES 8 -> 20 in the generated description

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 3: Track B — force HF Hub offline, recover once on cache miss

**Files:**
- Modify: [`biblio/embed.py`](../../../biblio/embed.py) — module top (after `import numpy`), `_model()`
- Test: `tests/test_robustness.py`

- [ ] **Step 1: Write the failing tests**

```python
import importlib
import os


def test_importing_embed_forces_hub_offline(monkeypatch):
    monkeypatch.delenv("HF_HUB_OFFLINE", raising=False)
    monkeypatch.delenv("HF_HUB_DISABLE_TELEMETRY", raising=False)
    import biblio.embed
    importlib.reload(biblio.embed)
    assert os.environ["HF_HUB_OFFLINE"] == "1"
    assert os.environ["HF_HUB_DISABLE_TELEMETRY"] == "1"


def test_model_retries_online_when_offline_load_fails(monkeypatch):
    import biblio.embed as e
    e._model.cache_clear()
    seen = []

    class FakeST:
        def __init__(self, name):
            seen.append(os.environ.get("HF_HUB_OFFLINE"))
            if len(seen) == 1:
                raise OSError("model not in cache")

    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setattr("sentence_transformers.SentenceTransformer", FakeST)

    e._model()

    assert seen == ["1", None]  # first attempt offline, retry with the var cleared
    assert os.environ["HF_HUB_OFFLINE"] == "1"  # restored afterwards
    e._model.cache_clear()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/c/Users/Usuario/.conda/envs/alcoa/python.exe -m pytest tests/test_robustness.py -k "hub_offline or retries_online" -v`
Expected: FAIL — env vars not set on import; `_model()` has no retry.

- [ ] **Step 3: Implement**

[`biblio/embed.py`](../../../biblio/embed.py) — after the stdlib imports, before `import numpy as np`:

```python
import functools
import os
import re
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")

import numpy as np
```

Replace `_model()`:

```python
@functools.lru_cache(maxsize=1)
def _model():
    from sentence_transformers import SentenceTransformer
    try:
        return SentenceTransformer(MODEL)
    except Exception:
        # genuine first run: model not cached. Drop offline, retry once, restore.
        prev = os.environ.pop("HF_HUB_OFFLINE", None)
        try:
            return SentenceTransformer(MODEL)
        finally:
            if prev is not None:
                os.environ["HF_HUB_OFFLINE"] = prev
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/c/Users/Usuario/.conda/envs/alcoa/python.exe -m pytest tests/test_robustness.py -k "hub_offline or retries_online" tests/test_search.py -v`
Expected: PASS (search tests still load the real cached model with offline forced).

- [ ] **Step 5: Commit**

```bash
rtk git add biblio/embed.py tests/test_robustness.py && rtk git commit -m "perf(embed): force HF_HUB_OFFLINE, recover once on cache miss

Every biblio search revalidated the cached model against the HF Hub and
printed an unauthenticated-request warning. The model is already cached;
setdefault lets an operator override with HF_HUB_OFFLINE=0.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 4: Track C — `biblio update` prints the command on Windows

**Files:**
- Modify: [`biblio/cli.py:197-201`](../../../biblio/cli.py) — the `update` branch
- Test: `tests/test_robustness.py`

- [ ] **Step 1: Write the failing test**

```python
import sys

from biblio.cli import main


def test_update_on_windows_prints_command_and_does_not_run(monkeypatch, capsys):
    monkeypatch.setattr(sys, "platform", "win32")
    calls = []
    monkeypatch.setattr("subprocess.run", lambda *a, **k: calls.append(a))

    rc = main(["update"])

    assert rc == 0
    assert calls == []
    out = capsys.readouterr().out
    assert "pip install --upgrade git+https://github.com/PedroHCosme/biblio.git" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/c/Users/Usuario/.conda/envs/alcoa/python.exe -m pytest tests/test_robustness.py::test_update_on_windows_prints_command_and_does_not_run -v`
Expected: FAIL — `subprocess.run` is called.

- [ ] **Step 3: Implement**

Replace the `update` branch in [`biblio/cli.py`](../../../biblio/cli.py):

```python
    if args.command == "update":
        url = "git+https://github.com/PedroHCosme/biblio.git"
        if sys.platform == "win32":
            print("biblio can't update itself on Windows (the running .exe is locked).\n"
                  "Run this in a fresh shell:\n\n"
                  f"  {sys.executable} -m pip install --upgrade {url}")
            return 0
        import subprocess
        print(f"Updating from {url} ...")
        return subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", url]).returncode
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/c/Users/Usuario/.conda/envs/alcoa/python.exe -m pytest tests/test_robustness.py::test_update_on_windows_prints_command_and_does_not_run -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
rtk git add biblio/cli.py tests/test_robustness.py && rtk git commit -m "fix(cli): biblio update prints the pip command on Windows instead of failing

pip's uninstall step can't replace the running Scripts/biblio.exe (WinError 32).
POSIX keeps auto-update.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 5: Track D — `pipeline.survey()` folder triage aggregation

**Files:**
- Modify: [`biblio/pipeline.py`](../../../biblio/pipeline.py) — new `survey()` function, new `from collections import Counter` import
- Test: `tests/test_robustness.py`

- [ ] **Step 1: Write the failing test**

```python
from biblio import pipeline


def _blank_pdf(path, n_pages):
    import pymupdf
    doc = pymupdf.open()
    for _ in range(n_pages):
        doc.new_page()
    doc.save(path)
    doc.close()
    return path


def test_survey_aggregates_ocr_pages_and_flags_over_cap(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "note.md").write_text("# x\ny", encoding="utf-8")
    big = _blank_pdf(src / "big.pdf", 4)      # 4 OCR pages
    small = _blank_pdf(src / "small.pdf", 1)  # 1 OCR page

    report = pipeline.survey(src, max_ocr_pages=2)

    assert report["total_ocr"] == 5
    assert report["by_ext"] == {".md": 1, ".pdf": 2}
    assert set(report["over_cap"]) == {big}
    assert small not in report["over_cap"]
    assert report["max_ocr_pages"] == 2


def test_survey_zero_cap_flags_nothing(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    _blank_pdf(src / "big.pdf", 4)
    assert pipeline.survey(src, max_ocr_pages=0)["over_cap"] == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/c/Users/Usuario/.conda/envs/alcoa/python.exe -m pytest tests/test_robustness.py -k survey -v`
Expected: FAIL — `AttributeError: module 'biblio.pipeline' has no attribute 'survey'`.

- [ ] **Step 3: Implement**

[`biblio/pipeline.py`](../../../biblio/pipeline.py) — add `from collections import Counter` near the top, and:

```python
def survey(target: Path | str, max_ocr_pages: int = 25) -> dict:
    """Folder-wide triage: doc counts, OCR-page total, files over the cap.

    Pure — writes nothing. Used by `biblio add --dry-run` and by the CLI's
    pre-ingest cap gate. `max_ocr_pages` 0 disables the over-cap flagging.
    """
    files = _files(Path(target))
    by_ext = Counter(f.suffix.lower() for f in files)
    ocr_by_file = {f: len(triage(f)["ocr"])
                   for f in files if f.suffix.lower() == ".pdf"}
    over_cap = ({f: n for f, n in ocr_by_file.items() if n > max_ocr_pages}
                if max_ocr_pages else {})
    return {"files": files, "by_ext": dict(by_ext), "ocr_by_file": ocr_by_file,
            "total_ocr": sum(ocr_by_file.values()), "over_cap": over_cap,
            "max_ocr_pages": max_ocr_pages}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/c/Users/Usuario/.conda/envs/alcoa/python.exe -m pytest tests/test_robustness.py -k survey -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
rtk git add biblio/pipeline.py tests/test_robustness.py && rtk git commit -m "feat(pipeline): survey() folder-wide triage aggregation

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 6: Track D — `ingest(exclude=...)` and the end-of-run skip report

**Files:**
- Modify: [`biblio/pipeline.py`](../../../biblio/pipeline.py) — `ingest()` signature + loop + trailing report
- Test: `tests/test_robustness.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path


def test_ingest_skips_excluded_files_and_reports_them(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "keep.md").write_text("# Scope\n" + "technical text. " * 40, encoding="utf-8")
    (src / "huge.md").write_text("# Big\n" + "text. " * 40, encoding="utf-8")
    out = tmp_path / "lib"
    msgs = []

    count = pipeline.ingest(src, output=out, exclude=frozenset({src / "huge.md"}),
                            warn=msgs.append)

    assert (out / "keep").is_dir()
    assert not (out / "huge").exists()
    assert count["skipped"] == 1
    assert any("over OCR budget" in m for m in msgs)
    assert any("huge" in m for m in msgs)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/c/Users/Usuario/.conda/envs/alcoa/python.exe -m pytest tests/test_robustness.py::test_ingest_skips_excluded_files_and_reports_them -v`
Expected: FAIL — `ingest()` has no `exclude` parameter (`TypeError`).

- [ ] **Step 3: Implement**

[`biblio/pipeline.py`](../../../biblio/pipeline.py) — `ingest()` signature adds `exclude`:

```python
def ingest(target: Path | str, output: Path | str | None = None, device: str = "auto",
           force: bool = False, warn=print, ask=None,
           summary: str = "auto", max_size_mb: float | None = None,
           fast: bool = False, exclude=frozenset()) -> dict[str, int]:
```

In the loop, before the `try`:

```python
    for f in _files(Path(target)):
        if f in exclude:
            count["skipped"] += 1
            continue
        try:
            ...
```

After the loop, before `return count`:

```python
    if exclude:
        warn("\nskipped (over OCR budget):")
        for f in sorted(exclude):
            warn(f'  {f.stem}  — run: biblio add "{f}" --fast   '
                 f'(or --max-ocr-pages 0)')
    return count
```

Add one line to the docstring: `` `exclude`: paths to skip (the CLI's over-OCR-cap set). ``

- [ ] **Step 4: Run test to verify it passes**

Run: `/c/Users/Usuario/.conda/envs/alcoa/python.exe -m pytest tests/test_robustness.py::test_ingest_skips_excluded_files_and_reports_them tests/test_idempotency.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
rtk git add biblio/pipeline.py tests/test_robustness.py && rtk git commit -m "feat(pipeline): ingest(exclude=...) skips files and reports them at the end

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 7: Track D.2 / D.3 — wire `--dry-run`, `--max-ocr-pages`, `--yes` into the CLI

**Files:**
- Modify: [`biblio/cli.py`](../../../biblio/cli.py) — `add` subparser, `add` branch, new helpers
- Test: `tests/test_robustness.py`

- [ ] **Step 1: Write the failing tests**

```python
import numpy as np
import pytest

from biblio import cli
from biblio.cli import main


@pytest.fixture
def stub_heavy(monkeypatch):
    """Keep CLI add tests off the real model and the real ~/.claude skill dir."""
    monkeypatch.setattr("biblio.pipeline.embed.vectorize",
                        lambda texts: np.zeros((len(texts), 384), dtype="float32"))
    monkeypatch.setattr("biblio.cli.skill.install", lambda *a, **k: None)
    monkeypatch.setattr("biblio.cli.index.generate", lambda *a, **k: None)
    monkeypatch.setattr("biblio.version_check.check", lambda *a, **k: None)


def _blank_pdf(path, n_pages):
    import pymupdf
    doc = pymupdf.open()
    for _ in range(n_pages):
        doc.new_page()
    doc.save(path)
    doc.close()
    return path


def test_dry_run_prints_estimate_and_writes_nothing(tmp_path, capsys, stub_heavy):
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.md").write_text("# x\ny", encoding="utf-8")
    _blank_pdf(src / "big.pdf", 4)
    out = tmp_path / "lib"

    rc = main(["--out", str(out), "add", str(src), "--dry-run", "--max-ocr-pages", "2"])

    assert rc == 0
    assert not out.exists()  # no bibliotheca created
    report = capsys.readouterr().out
    assert "OCR pages total: 4" in report
    assert "big" in report and "Over --max-ocr-pages (2)" in report


def test_add_yes_skips_over_cap_file_processes_the_rest(tmp_path, capsys, stub_heavy):
    src = tmp_path / "src"
    src.mkdir()
    (src / "keep.md").write_text("# Scope\n" + "technical text. " * 40, encoding="utf-8")
    _blank_pdf(src / "big.pdf", 4)
    out = tmp_path / "lib"

    rc = main(["--out", str(out), "add", str(src), "--yes", "--max-ocr-pages", "2"])

    assert (out / "keep").is_dir()
    assert not (out / "big").exists()
    assert "skipped (over OCR budget)" in capsys.readouterr().out
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/c/Users/Usuario/.conda/envs/alcoa/python.exe -m pytest tests/test_robustness.py -k "dry_run or over_cap_file" -v`
Expected: FAIL — `add` has no `--dry-run` / `--max-ocr-pages` / `--yes` (`SystemExit: 2` from argparse).

- [ ] **Step 3: Add the flags**

In `main()`, on the `add` subparser (`a`):

```python
    a.add_argument("--dry-run", action="store_true",
                   help="triage the folder, print the OCR estimate, write nothing")
    a.add_argument("--max-ocr-pages", type=int, default=25, metavar="N",
                   help="hold back files needing more than N OCR pages (0 = no cap)")
    a.add_argument("--yes", action="store_true",
                   help="non-interactive: skip files over --max-ocr-pages without asking")
```

- [ ] **Step 4: Add the helpers** (module level in `cli.py`)

```python
def _choose(text: str, options: str, default: str) -> str:
    raw = input(f"{text} ").strip().lower()
    return raw[:1] if raw[:1] in options else default


def _minutes(ocr_pages: int) -> int:
    return round(ocr_pages * 30 / 60)  # ~30s/page on CPU


def _print_survey(report: dict, target: Path) -> None:
    by_ext = report["by_ext"]
    exts = ", ".join(f"{n} {ext}" for ext, n in sorted(by_ext.items()))
    total = report["total_ocr"]
    print(f"\n  {sum(by_ext.values())} documents  ({exts})")
    print(f"  OCR pages total: {total}  (~{_minutes(total)} min on CPU)")
    over = report["over_cap"]
    if over:
        print(f"\n  Over --max-ocr-pages ({report['max_ocr_pages']}):")
        for f, n in sorted(over.items(), key=lambda kv: -kv[1]):
            print(f"    {f.stem:<45} {n} OCR pages  (~{_minutes(n)} min)")
        print(f"\n  Proceed: biblio add {target}                 # prompts about the files above")
        print(f"           biblio add {target} --yes           # skips them, indexes the rest")
        print(f"           biblio add {target} --max-ocr-pages 0   # OCR everything, no cap")


def _over_cap_exclude(report: dict, interactive: bool):
    """Returns the set of paths to exclude, or None to abort the run."""
    over = report["over_cap"]
    if interactive:
        choice = _choose(
            f"{len(over)} files exceed the OCR cap "
            f"(~{_minutes(sum(over.values()))} min total). "
            "[p]roceed with all / [s]kip them / [a]bort?", "psa", "s")
        if choice == "p":
            return frozenset()
        if choice == "a":
            return None
    return frozenset(over)
```

- [ ] **Step 5: Rewrite the `add` branch**

```python
    if args.command == "add":
        target = Path(args.target)
        report = (pipeline.survey(target, args.max_ocr_pages)
                  if args.dry_run or (target.is_dir() and args.max_ocr_pages)
                  else None)
        if args.dry_run:
            _print_survey(report, target)
            return 0

        exclude = frozenset()
        if report and report["over_cap"]:
            interactive = not args.yes and sys.stdin.isatty()
            exclude = _over_cap_exclude(report, interactive)
            if exclude is None:
                print("aborted.")
                return 1

        ask = None if args.yes else _confirm
        count = pipeline.ingest(target, output=args.out, device=args.device,
                                force=args.force, ask=ask,
                                summary=args.summary_mode, max_size_mb=args.max_size,
                                fast=args.fast, exclude=exclude)
        index.generate(output=args.out, summary="no")
        if count["ok"]:
            skill.install()
        print(f"\n{count['ok']} processed, {count['skipped']} unchanged, "
              f"{count['failed']} failed")
        return 1 if count["failed"] else 0
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `/c/Users/Usuario/.conda/envs/alcoa/python.exe -m pytest tests/test_robustness.py -k "dry_run or over_cap_file" -v`
Expected: PASS

- [ ] **Step 7: Full suite**

Run: `rtk vitest run 2>/dev/null; /c/Users/Usuario/.conda/envs/alcoa/python.exe -m pytest -q`
Expected: PASS (all pre-existing tests still green).

- [ ] **Step 8: Commit**

```bash
rtk git add biblio/cli.py tests/test_robustness.py && rtk git commit -m "feat(cli): biblio add --dry-run / --max-ocr-pages / --yes

--dry-run triages the folder and prints the OCR estimate without writing.
A folder add holds back files over the cap: prompt on a TTY, skip-and-report
under --yes or no TTY.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 8: Track D.4 — `auto` summaries confirm once per run

**Files:**
- Modify: [`biblio/ollama.py:48-60`](../../../biblio/ollama.py) — `wants_summary()`
- Test: `tests/test_robustness.py`

- [ ] **Step 1: Write the failing test**

```python
from biblio import ollama


def test_auto_summary_prompts_once_and_defaults_no(monkeypatch):
    monkeypatch.setattr(ollama, "available", lambda: True)
    monkeypatch.setattr(ollama, "_has_model", lambda: True)

    assert ollama.wants_summary("auto", ask=lambda _t: False) is False
    assert ollama.wants_summary("auto", ask=lambda _t: True) is True
    assert ollama.wants_summary("auto", ask=None) is False


def test_explicit_no_summary_never_prompts(monkeypatch):
    monkeypatch.setattr(ollama, "available", lambda: True)
    monkeypatch.setattr(ollama, "_has_model", lambda: True)
    boom = lambda _t: (_ for _ in ()).throw(AssertionError("should not ask"))
    assert ollama.wants_summary("no", ask=boom) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/c/Users/Usuario/.conda/envs/alcoa/python.exe -m pytest tests/test_robustness.py -k "auto_summary or explicit_no_summary" -v`
Expected: FAIL — `auto` returns `True` without asking when Ollama is ready.

- [ ] **Step 3: Implement**

[`biblio/ollama.py`](../../../biblio/ollama.py) — in `wants_summary()`, after the `mode == "no"` check:

```python
def wants_summary(mode: str, ask=None, warn=print) -> bool:
    """Mode -> 'can we summarize now?'.

    'no': never. 'auto' (default): only if Ollama+model are already ready, and
    then only after confirming once (default no; `ask` None resolves to no).
    'yes': asks and installs what's missing.
    """
    if mode == "no":
        return False
    if mode == "auto" and available() and _has_model():
        if ask is None:
            return False
        return ask("Ollama detected — generate per-document summaries "
                   "(~75s each, CPU)?")
    ok = ensure(ask, allow_install=(mode == "yes"))
    if not ok:
        warn("summaries: Ollama unavailable, continuing without" if mode == "yes"
             else "summaries: Ollama not configured, skipping (--summary enables)")
    return ok
```

(`_confirm` / `ensure`'s `ask` callbacks already append `[y/N]`, so the prompt text omits it.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `/c/Users/Usuario/.conda/envs/alcoa/python.exe -m pytest tests/test_robustness.py -k "auto_summary or explicit_no_summary" tests/test_summarize.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
rtk git add biblio/ollama.py tests/test_robustness.py && rtk git commit -m "fix(ollama): auto summaries confirm once per run instead of silently on

SKILL.md says summaries are opt-in, but auto mode summarized every doc
(~75-180s each) for anyone who once ran --summary. --summary / --no-summary
bypass the prompt; ask=None (GUI / non-interactive) resolves to no.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 9: Track A′ — teach Claude the same knobs

**Files:**
- Modify: [`biblio/skill.py`](../../../biblio/skill.py) — `PROTOCOL` string
- Test: `tests/test_robustness.py`

- [ ] **Step 1: Write the failing test**

```python
from biblio import skill


def test_protocol_teaches_folder_ingest_knobs():
    for text in (skill.skill_text(), skill.claude_md_text()):
        assert "--dry-run" in text
        assert "--max-ocr-pages" in text
        assert "Ingesting a folder" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/c/Users/Usuario/.conda/envs/alcoa/python.exe -m pytest tests/test_robustness.py::test_protocol_teaches_folder_ingest_knobs -v`
Expected: FAIL — `PROTOCOL` says nothing about `--dry-run`.

- [ ] **Step 3: Implement**

[`biblio/skill.py`](../../../biblio/skill.py) — insert this section into `PROTOCOL`, immediately before `## Other commands` (keep the `{command}` placeholder; add no literal `{`/`}` — `PROTOCOL` is `.format()`-ed):

```
## Ingesting a folder

Before ingesting a folder for the user, estimate the cost first:

```bash
{command} add <folder> --dry-run
```

Show them the document count and the OCR-page estimate. If any file is flagged
over the OCR cap, put the choice to the user — index that file `--fast` (native
text only, scanned pages come out empty), raise `--max-ocr-pages`, or skip it.
Do **not** pass `--yes` past the cap without their OK.

Summaries stay opt-in: pass `--summary` only if the user asked. A plain `add`
prompts once if Ollama is installed.

```

- [ ] **Step 4: Run test to verify it passes**

Run: `/c/Users/Usuario/.conda/envs/alcoa/python.exe -m pytest tests/test_robustness.py::test_protocol_teaches_folder_ingest_knobs -v`
Expected: PASS

- [ ] **Step 5: Full suite + commit**

Run: `/c/Users/Usuario/.conda/envs/alcoa/python.exe -m pytest -q`
Expected: PASS

```bash
rtk git add biblio/skill.py tests/test_robustness.py && rtk git commit -m "docs(skill): teach Claude the folder-ingest knobs (--dry-run, --max-ocr-pages)

Shared PROTOCOL string, so both the installed SKILL.md and the generated
CLAUDE.md get the section.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Verification checklist

- [ ] `/c/Users/Usuario/.conda/envs/alcoa/python.exe -m pytest -q` — all green
- [ ] `biblio search "x"` no longer prints the HF Hub warning and returns fast (manual, needs cached model)
- [ ] `biblio add <folder> --dry-run` prints the estimate and creates nothing
- [ ] `biblio update` on Windows prints the pip command, exits 0, changes nothing
- [ ] `biblio libs` lists a bibliotheca mid-ingest (start a folder `add`, Ctrl-C, check)

## Out of scope (from the spec)

- Release/version bump for `biblio update` to pull — handled separately by the maintainer.
- Passing precomputed triage routes from `survey()` into `_process_one()` to avoid the second per-PDF triage — the spec (D.5) accepts the ~1–2 min folder pass as the price of a real estimate; only `.pdf` files pay it twice and real corpora are mostly `.md`.
- Persistent search daemon, docling strategy changes, auto-`--fast` fallback, registry auto-pruning, `biblio search` returning content.
