# biblio

**A local document-memory layer for coding agents.** Point it at a pile of
`.pdf`, `.md` and `.txt` files; it gives back a folder of sliced, indexed,
self-describing Markdown whose search returns **pointers** (`file:line-range`)
instead of content — so an agent reads only the paragraph it actually needs,
without anyone having to teach it how.

```
$ biblio search "anchorage length of passive reinforcement"
C:\Users\you\biblio\nbr-6118\09-ancoragem.md:112-195  0.031  9.4 Comprimento de ancoragem
C:\Users\you\biblio\nbr-6118\07-cobrimento.md:6-44     0.018  7.4 Cobrimento nominal
```

The agent then opens `09-ancoragem.md` with `offset=112, limit=84` — nothing
else enters its context.

---

## Why

Feeding whole documents to an agent is expensive and noisy. RAG stacks that
return raw chunks still dump prose into the context window and usually need a
server. `biblio` takes a different position:

| | Typical RAG / "chat with your docs" | biblio |
|---|---|---|
| What search returns | text chunks | **pointers** (`file:line-range`, score, heading) |
| Context cost of 3 lookups | thousands of tokens | ~900 tokens |
| Infrastructure | vector DB / server | one SQLite file inside the library folder |
| Portability | re-index on move | copy the folder — no absolute paths inside |
| Teaching the agent | prompt engineering | a skill that installs itself |

A single PDF page sent natively to an LLM API costs more than three `biblio`
lookups. The library folder is also just *readable Markdown* — if the search
binary isn't around, `grep` on `INDEX.md` still works.

## How it works

A six-stage pipeline, each stage writing its result to disk:

```
triage → convert → normalize → slice → summarize → index
```

- **triage** — per page, decide the cheapest converter (native text / complex
  layout / OCR).
- **convert** — `pymupdf4llm` for native pages, Docling (+ RapidOCR) for the
  rest; page-provenance markers are carried through.
- **normalize** — deterministic cleanup: de-hyphenation, repeated
  headers/footers, stray page numbers, heading hierarchy.
- **slice** — cut into one file per heading, with a floor (tiny sections merge)
  and a ceiling (huge sections split on paragraph boundaries). Each slice keeps
  its exact source line range and its parent heading.
- **summarize** — one summary and a keyword line per document (optional, via a
  local Ollama model). Never per chunk.
- **index** — generate `INDEX.md` (a `grep` target, one block per document) and
  `CLAUDE.md` (so pointing an agent at the folder is enough).

Search is **hybrid** — semantic (vector) + literal (SQLite FTS5) — fused by
Reciprocal Rank Fusion, deduplicated per file, returning the best pointer for
each. Cross-lingual works: a Portuguese question reaches an English datasheet in
the same library, and vice-versa.

## Stack

Python 3.12 · PyMuPDF + `pymupdf4llm` · Docling (+ RapidOCR) ·
`sentence-transformers` (`paraphrase-multilingual-MiniLM-L12-v2`, 384-dim,
CPU) · SQLite (FTS5 + brute-force vector search in NumPy — measured at ~29 ms
over 500k chunks, so no native extension needed) · Ollama / `qwen3:1.7b`
(optional; CPU-friendly) · Gradio · pytest

## Install

```bash
conda create -n biblio python=3.12 -y
conda activate biblio
pip install -e .
biblio shortcut     # desktop shortcut for the GUI + installs the Claude Code skill
```

No desktop shortcut wanted? Install just the Claude Code skill:

```bash
biblio skill
```

(`biblio add` and `biblio index` also (re)install the skill, so this is only
needed to set it up before the first ingestion.)

Docling pulls PyTorch (~2 GB) on first install; the embedding model (~500 MB)
downloads on first search.

## Ollama (optional — for summaries)

Ollama runs a small local model (`qwen3:1.7b`, ~1.4 GB) that writes one summary
and a keyword line per document. Those keyword lines become the `**Terms:**`
entries in `INDEX.md` — the fallback path an agent uses to find an exact
identifier ("NBR 6118", "9.4.2") when semantic search misses it.

**Without Ollama, everything else works.** Ingestion, slicing, hybrid search and
pointers are unaffected. You only lose the per-document summary and the
`**Terms:**` safety net; documents show up as `summary pending` in
`biblio status`.

**Auto-install.** On the first `biblio add`, if Ollama is not installed, biblio
asks (once) and, on yes, installs it via `winget` and pulls the model. If Ollama
is already installed but the model is missing, biblio asks to pull just the model.
It never installs anything silently.

**Manual / on another machine:**

```bash
winget install -e --id Ollama.Ollama
ollama pull qwen3:1.7b
biblio index                # backfill summaries for documents already ingested
```

`biblio index` only (re)generates summaries for documents marked pending; use
`biblio add <source> --force` to regenerate everything. On a GPU box you can bump
the model to `qwen3:4b` in `biblio/ollama.py` for slightly better summaries.

## CLI

```
biblio [--out <library>] <command> [options]
```

`--out` selects the library to act on. It accepts a **name** (stored under
`~/biblio/<slug>`) or a **path**. Omit it and commands act on the default
library, `~/biblio/geral`. `--out` goes before the command.

### `biblio add <path>` — ingest

```bash
biblio add report.pdf                         # one file (.pdf, .md or .txt)
biblio add ~/Documents/standards              # a folder, recursive
biblio add ~/Documents/standards --out physics   # into a named library
biblio add ~/Documents/standards --force      # reprocess even if unchanged
biblio add scan.pdf --device cuda             # auto | cpu | cuda for Docling
```

Re-running on a folder is cheap and safe: unchanged files are skipped by SHA-256,
only new or edited files are processed. A password-protected or corrupt PDF in a
batch is marked `failed` and the batch continues. Exit code is `1` if anything
failed, `0` otherwise. After a successful add, `INDEX.md`/`CLAUDE.md` are
regenerated and the Claude Code skill is (re)installed.

### `biblio search "<query>"` — the core command

```bash
biblio search "synchronous speed of the rotating field"
biblio search "slip"            --lib physics        # one library (name or path)
biblio search "torque"          --doc aula-9         # one document
biblio search "eddy losses"     --top 10             # more hits (default 5)
biblio search "rotor bar"       --json               # machine-readable
```

With no `--lib`/`--out`, search covers **every registered library** on the
machine. Output is one line per hit — **a pointer, never the text**:

```
C:\Users\you\biblio\nbr-6118\09-ancoragem.md:112-195  0.031  9.4 Comprimento de ancoragem
└─ absolute path ────────────────────────┘ └ lines ┘  score  └ heading ────────────┘
```

Read the hit with `Read`/`sed`/an editor at `offset = 112`, `limit = 195 - 112 + 1`.
`--json` emits `[{"caminho","doc","arquivo","secao","linha_ini","linha_fim","score"}, …]`.
Empty result prints `nada encontrado`. Pointing `--lib` at a folder that isn't a
biblio library is an error (not a silent zero), with the command to fix it.

### Housekeeping

```bash
biblio index      # rebuild INDEX.md + CLAUDE.md, backfill pending summaries, reinstall skill
biblio status     # per-document: pages/format, slice count, ok | failed | summary pending
biblio libs       # registered libraries, most-recently-used first
biblio skill      # install the Claude Code skill only (no shortcut)
biblio gui        # Gradio ingestion panel on http://127.0.0.1:7860
biblio shortcut   # desktop .lnk for the GUI + install the Claude Code skill
```

When semantic search misses an exact identifier ("NBR 6118", "9.4.2"), grep the
index instead:

```bash
grep -A4 -i "NBR 6118" ~/biblio/<library>/INDEX.md
```

Each document is one block; the `**Terms:**` line (populated by Ollama) is the
recovery path. Never read `INDEX.md` whole — it is built for `grep`.

### Getting the most out of it

1. **Keep Ollama running during ingestion** — populates the `**Terms:**` line.
2. **One subject per library** — search with no flag spans them all; separate them
   and you can scope later with `--lib`.
3. **Rewrite the query in domain terms.** "How much rebar to anchor?" searches
   badly; "anchorage length passive reinforcement" searches well.
4. **Drill with `--doc`** once you've found the right document.

## Claude Code integration

Nothing to wire up. The skill installs itself to `~/.claude/skills/biblioteca/`
on `biblio shortcut` and after every successful ingestion. In a fresh Claude
Code session, a question a document can answer makes the agent run
`biblio search` on its own — and read only the returned line range.

**To scope a project to one library**, point the agent at that library's folder
(or copy the folder into the project). Its `CLAUDE.md` teaches the agent to
search with `--lib`, so results stay inside that one collection.

## Platforms

Windows, macOS and Linux. The pipeline, search, GUI and skill are pure
`pathlib` + cross-platform deps. Two things are Windows-only and degrade
cleanly elsewhere:

- **`biblio shortcut`** creates a `.lnk` on Windows; on macOS/Linux it just
  installs the skill and tells you to run `biblio gui`.
- **Ollama auto-install** uses `winget`. On macOS/Linux `biblio` prints the
  right command instead (`brew` / `ollama.com/install.sh`) — nothing crashes.

## Portability

A library folder can be moved, renamed, or copied to another machine with **no
fix-up** — it contains no absolute paths. Install `biblio` on the target and the
first `--lib` search registers it. What doesn't travel: the embedding model
(re-downloaded on first search).

## Limitations

- **OCR-quality detection is not implemented** — `quality` is always `ok`.
  `INDEX.md` already renders a warning banner when the field is `low`; the
  detector lands when the first genuinely bad scan shows up in a real corpus.
- **Documents without Markdown headings** (a lot of legal text — "Art. 5º",
  "§ 1º" come out as plain paragraphs) fall through to numbered parts. Search
  still works; structure is lost. Fix is to teach `normalize.py` to recognize
  those as headings.
- **Cross-lingual retrieval** depends on the embedding model; it was validated
  PT↔EN, not guaranteed for every language pair.

## License

MIT
