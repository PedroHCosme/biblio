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

## Tech

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
biblio shortcut     # desktop shortcut + installs the Claude Code skill
```

Docling pulls PyTorch (~2 GB) on first install; the embedding model (~500 MB)
downloads on first search. Ollama is optional — without it everything runs
except per-document summaries and the `Terms:` line in `INDEX.md`.

## Use

```bash
biblio gui                                   # ingestion panel (or the shortcut)
biblio add ~/Documents/standards             # a file or a whole folder (recursive)
biblio add ~/Documents/standards --out physics   # a named library, one subject each
biblio search "rotor bar equation"           # covers every known library
biblio search "slip" --lib physics --top 10  # scope to one library
biblio search "torque" --doc aula-9 --json   # scope to one document, machine output
biblio index                                 # regenerate INDEX.md / CLAUDE.md
biblio status                                # what went in, what failed, what's pending
biblio libs                                  # registered libraries
```

Re-running `biblio add` on a folder is cheap and safe: unchanged files are
skipped by content hash, only new material is processed. A password-protected or
corrupt PDF in a batch is marked `failed` and the batch continues.

### Getting the most out of it

1. **Keep Ollama running during ingestion** — that populates the `Terms:` line
   in `INDEX.md`, the fallback path for exact identifiers ("NBR 6118", "9.4.2")
   that semantic search can miss.
2. **One subject per library.** Search with no flag spans every library on the
   machine; separate them and you can scope later.
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
