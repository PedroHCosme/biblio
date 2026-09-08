# English Rename Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rename all Portuguese identifiers, strings, and persisted data keys to English across the entire `biblio` codebase. Single commit, version bump to 0.2.0.

**Architecture:** Big-bang rename — all source files change, tests run only after ALL renames are complete (cross-module references break mid-rename). Automatic migration of `_meta.yaml` and SQLite schema so existing bibliothecas reindex transparently.

**Tech Stack:** Python 3.11+, no new dependencies.

**Spec:** `docs/superpowers/specs/2026-09-08-english-rename-design.md`

**Constraints:**
- No `Co-Authored-By` in commit messages
- Ollama prompt stays in Portuguese (user decision)
- Portuguese stopwords in `search.py` stay (linguistic data)
- Test corpus text stays in Portuguese (real domain data)
- Package name `biblio` and concept `bibliotheca` stay

---

## File Map

| Layer | Files | Scope |
|---|---|---|
| Leaf | `meta.py`, `paths.py`, `triage.py`, `normalize.py`, `version_check.py`, `shortcut.py` | Functions, constants, YAML keys, migration |
| Utility | `ollama.py`, `convert.py` | Functions, constants, user-facing strings |
| Intermediate | `embed.py`, `slice.py`, `db.py`, `summarize.py` | Dict keys, classes, SQL schema |
| Orchestration | `search.py`, `index.py`, `skill.py`, `pipeline.py` | Functions, output keys, English text |
| Interface | `cli.py`, `gui.py` | Help text, labels, messages |
| Tests | `conftest.py`, `test_*.py` (7 files) | Fixture/test names, assertions |
| Config | `pyproject.toml` | Version bump, description |

---

### Task 1: `biblio/meta.py` — migration logic + rename

**Files:**
- Modify: `biblio/meta.py`

This is the foundation: every other module depends on meta keys being stable. The migration function translates old Portuguese keys on read and deletes `hash` to force reindexation.

- [ ] **Step 1: Read `biblio/meta.py`**

- [ ] **Step 2: Rewrite `biblio/meta.py` with migration and English identifiers**

```python
"""`_meta.yaml`: provenance, hash, and state. Makes reprocessing a folder cheap."""
import hashlib
from datetime import date
from pathlib import Path

import yaml

FILENAME = "_meta.yaml"

_KEY_MAP = {
    "origem": "source", "formato": "format", "paginas": "pages",
    "rota": "route", "data": "date", "qualidade": "quality",
    "falhou": "failed", "resumo": "summary", "fatias": "slices",
    "termos": "terms",
}
_ROUTE_MAP = {"nativa": "native", "complexa": "complex"}


def _migrate(data: dict) -> dict:
    """Translate old Portuguese keys to English. Deletes hash to force reindex."""
    changed = False
    for old, new in _KEY_MAP.items():
        if old in data and new not in data:
            data[new] = data.pop(old)
            changed = True
    if "route" in data and isinstance(data["route"], dict):
        for old, new in _ROUTE_MAP.items():
            if old in data["route"]:
                data["route"][new] = data["route"].pop(old)
                changed = True
    if data.get("summary") == "pendente":
        data["summary"] = "pending"
        changed = True
    if data.get("quality") == "baixa":
        data["quality"] = "low"
        changed = True
    if changed:
        data.pop("hash", None)
    return data


def hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read(doc_dir: Path) -> dict:
    f = doc_dir / FILENAME
    if not f.exists():
        return {}
    data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
    migrated = _migrate(data)
    if "hash" not in migrated and any(k in migrated for k in _KEY_MAP.values()):
        write(doc_dir, migrated)
    return migrated


def write(doc_dir: Path, data: dict) -> None:
    doc_dir.mkdir(parents=True, exist_ok=True)
    (doc_dir / FILENAME).write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )


def already_processed(doc_dir: Path, digest: str) -> bool:
    """Same hash and no recorded failure: nothing to redo."""
    prev = read(doc_dir)
    return prev.get("hash") == digest and not prev.get("failed")


def new_record(path: Path, digest: str, route: dict[str, list[int]]) -> dict:
    """Empty route = source was already text (.md, .txt): no pages, no OCR."""
    return {
        "source": str(path.resolve()),
        "format": path.suffix.lower().lstrip("."),
        "hash": digest,
        "pages": sum(len(v) for v in route.values()) or None,
        "route": {k: len(v) for k, v in route.items()},
        "date": date.today().isoformat(),
        "quality": "ok",
        "failed": None,
        "summary": "pending",
    }
```

- [ ] **Step 3: Verify the file is syntactically valid**

Run: `cd /c/Users/Usuario/pedrocosme/dev/fromPDFtoAgenticFriendly && /c/Users/Usuario/.conda/envs/alcoa/python.exe -c "import ast; ast.parse(open('biblio/meta.py').read()); print('OK')"`

---

### Task 2: `biblio/paths.py` + `biblio/triage.py` + `biblio/normalize.py` — leaf modules

**Files:**
- Modify: `biblio/paths.py`, `biblio/triage.py`, `biblio/normalize.py`

#### paths.py renames

| Old | New |
|---|---|
| `RAIZ` | `ROOT` |
| `BIBLIOTHECA_PADRAO` | `DEFAULT_BIBLIOTHECA` |
| `REGISTRO` | `REGISTRY` |
| `raiz()` | `root()` |
| `registrar()` | `register()` |
| `conhecidas_bibliotheca()` | `known_bibliothecas()` |
| `todas()` | `all_libs()` |
| docstring/comments | English |

- [ ] **Step 1: Rewrite `biblio/paths.py`**

```python
"""Where bibliothecas live and how names become paths."""
import re
import unicodedata
from pathlib import Path

ROOT = Path.home() / "biblio"
DEFAULT_BIBLIOTHECA = ROOT / "geral"

REGISTRY = Path.home() / ".biblio" / "bibliothecas.txt"


def slug(text: str, limit: int = 60) -> str:
    no_accent = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    clean = re.sub(r"[^a-z0-9]+", "-", no_accent.lower()).strip("-")
    return clean[:limit].rstrip("-") or "untitled"


def root(output: Path | str | None = None) -> Path:
    """Accepts name or path, symmetric with --lib in search."""
    if not output:
        return DEFAULT_BIBLIOTHECA
    text = str(output)
    return ROOT / slug(text) if Path(text).parent == Path(".") else Path(text)


def register(bibliotheca: Path) -> None:
    """Move the bibliotheca to the top of the list."""
    path = str(bibliotheca.resolve())
    known = [c for c in known_bibliothecas() if c != path]
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY.write_text("\n".join([path, *known]) + "\n", encoding="utf-8")


def known_bibliothecas() -> list[str]:
    """Most recent first. Removes entries deleted from disk."""
    if not REGISTRY.exists():
        return []
    return [line for line in REGISTRY.read_text(encoding="utf-8").splitlines()
            if line.strip() and Path(line).is_dir()]


def all_libs(output=None) -> list[Path]:
    """Bibliothecas to search: the requested one(s), or all known, or just the default."""
    if isinstance(output, (list, tuple)):
        return [Path(c) for c in output]
    if output:
        requested = Path(output)
        if requested.is_dir():
            return [requested]
        known = [c for c in known_bibliothecas() if Path(c).name == str(output)]
        return [Path(known[0])] if known else [requested]
    return [Path(c) for c in known_bibliothecas()] or [DEFAULT_BIBLIOTHECA]
```

#### triage.py renames

| Old | New |
|---|---|
| `LIMIAR_CARACTERES` | `CHAR_THRESHOLD` |
| `rotear_pagina()` | `route_page()` |
| `triar()` | `triage()` |
| route keys `"nativa"`, `"complexa"` | `"native"`, `"complex"` |
| docstring/comments | English |

- [ ] **Step 2: Rewrite `biblio/triage.py`**

```python
"""Decide which converter to use, page by page. Deterministic, no model."""
from pathlib import Path

import pymupdf

CHAR_THRESHOLD = 120


def route_page(n_chars: int, has_table: bool) -> str:
    """native (pymupdf4llm, fast) | complex (docling) | ocr (docling with OCR)."""
    if n_chars < CHAR_THRESHOLD:
        return "ocr"
    return "complex" if has_table else "native"


def triage(pdf_path: Path) -> dict[str, list[int]]:
    """Returns {'native': [...], 'complex': [...], 'ocr': [...]} with 1-based pages."""
    route: dict[str, list[int]] = {"native": [], "complex": [], "ocr": []}
    with pymupdf.open(pdf_path) as doc:
        for number, page in enumerate(doc, start=1):
            n = len(page.get_text().strip())
            has_table = n >= CHAR_THRESHOLD and bool(page.find_tables().tables)
            route[route_page(n, has_table)].append(number)
    return route
```

#### normalize.py renames

| Old | New |
|---|---|
| `LIMIAR_REPETICAO` | `REPETITION_THRESHOLD` |
| `MAX_CARACTERES_CABECALHO` | `MAX_HEADER_CHARS` |
| `normalizar()` | `normalize()` |
| internal functions/vars | English |
| docstring/comments | English |

- [ ] **Step 3: Rewrite `biblio/normalize.py`**

```python
"""Deterministic cleanup of raw markdown. No LLM here."""
import re
from collections import Counter

REPETITION_THRESHOLD = 3
MAX_HEADER_CHARS = 80

_BROKEN_HYPHEN = re.compile(r"(\w)-\n([a-zà-ÿ])")
_BARE_NUMBER = re.compile(r"^\s*\d{1,4}\s*$")
_PAGE_OF = re.compile(r"^\s*(p[áa]g(ina)?\.?\s*)?\d{1,4}\s*(de|/|of)\s*\d{1,4}\s*$", re.I)
_HEADING = re.compile(r"^(#{1,6})\s+\S")
_MARKER = re.compile(r"^<!-- pag \d+ -->$")
_LIST_ITEM = re.compile(r"^([-*+]\s|\d+[.)]\s)")
_EMPHASIS = "*_ "


def _strip_emphasis(line: str) -> str:
    return line.strip().strip(_EMPHASIS)


def _is_structure(line: str) -> bool:
    """Heading, list, table, or marker: never removed, no matter how often repeated."""
    stripped = line.strip()
    return bool(
        _HEADING.match(stripped)
        or _MARKER.match(stripped)
        or _LIST_ITEM.match(stripped)
        or stripped.startswith(("|", ">", "```"))
    )


def _remove_repeated(lines: list[str]) -> list[str]:
    candidates = Counter(
        _strip_emphasis(line) for line in lines
        if _strip_emphasis(line) and len(_strip_emphasis(line)) <= MAX_HEADER_CHARS
        and not _is_structure(line)
    )
    junk = {text for text, n in candidates.items() if n >= REPETITION_THRESHOLD}
    return [line for line in lines if _strip_emphasis(line) not in junk]


def _remove_page_numbers(lines: list[str]) -> list[str]:
    return [
        line for line in lines
        if not (_BARE_NUMBER.match(_strip_emphasis(line)) or _PAGE_OF.match(_strip_emphasis(line)))
    ]


def _promote_hierarchy(lines: list[str]) -> list[str]:
    levels = [len(m.group(1)) for line in lines if (m := _HEADING.match(line.strip()))]
    if not levels or min(levels) == 1:
        return lines
    delta = min(levels) - 1
    return [
        line[delta:] if _HEADING.match(line.strip()) and line.startswith("#") else line
        for line in lines
    ]


def normalize(markdown: str) -> str:
    text = _BROKEN_HYPHEN.sub(r"\1\2", markdown)
    lines = text.split("\n")
    lines = _remove_repeated(lines)
    lines = _remove_page_numbers(lines)
    lines = _promote_hierarchy(lines)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip() + "\n"
```

- [ ] **Step 4: Verify all three files parse**

Run: `cd /c/Users/Usuario/pedrocosme/dev/fromPDFtoAgenticFriendly && /c/Users/Usuario/.conda/envs/alcoa/python.exe -c "import ast; [ast.parse(open(f'biblio/{f}').read()) for f in ('paths.py','triage.py','normalize.py')]; print('OK')"`

---

### Task 3: `biblio/ollama.py` + `biblio/version_check.py` + `biblio/shortcut.py` — utility modules

**Files:**
- Modify: `biblio/ollama.py`, `biblio/version_check.py`, `biblio/shortcut.py`

#### ollama.py renames

| Old | New |
|---|---|
| `MODELO` | `MODEL` |
| `ENDERECO` | `ENDPOINT` |
| `INSTRUCAO_MANUAL` | `MANUAL_INSTRUCTIONS` |
| `instalado()` | `installed()` |
| `disponivel()` | `available()` |
| `quer_resumo()` | `wants_summary()` |
| `garantir()` | `ensure()` |
| `gerar()` | `generate()` |
| all user-facing strings | English |
| mode values `"nao"`, `"sim"` | `"no"`, `"yes"` |

- [ ] **Step 1: Rewrite `biblio/ollama.py`**

```python
"""Detection, consent-based installation, and calling of the local model."""
import json
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

# ponytail: 1.7b measured on real corpus: 4b takes ~180s/doc on CPU, 1.7b ~75s/doc.
MODEL = "qwen3:1.7b"
ENDPOINT = "http://localhost:11434/api/generate"

_INSTALL_OLLAMA = {
    "win32": "winget install -e --id Ollama.Ollama",
    "darwin": "brew install ollama   (or download from https://ollama.com/download)",
}.get(sys.platform, "curl -fsSL https://ollama.com/install.sh | sh")

MANUAL_INSTRUCTIONS = (
    "Install manually:\n"
    f"  {_INSTALL_OLLAMA}\n"
    f"  ollama pull {MODEL}\n"
    "Then run `biblio index` to generate pending summaries."
)


def installed() -> bool:
    return shutil.which("ollama") is not None


def available() -> bool:
    try:
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2)
        return True
    except (urllib.error.URLError, OSError):
        return False


def _has_model() -> bool:
    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2) as r:
            names = [m["name"] for m in json.load(r).get("models", [])]
        return any(n == MODEL or n.startswith(MODEL + "@") for n in names)
    except (urllib.error.URLError, OSError, ValueError, KeyError):
        return False


def wants_summary(mode: str, ask=None, warn=print) -> bool:
    """Mode -> 'can we summarize now?'.

    'no': never. 'auto' (default): only if Ollama+model are already ready,
    never downloads. 'yes': asks and installs what's missing.
    """
    if mode == "no":
        return False
    ok = ensure(ask, allow_install=(mode == "yes"))
    if not ok:
        warn("summaries: Ollama unavailable, continuing without" if mode == "yes"
             else "summaries: Ollama not configured, skipping (--summary enables)")
    return ok


def ensure(ask=None, *, allow_install: bool = False) -> bool:
    """Returns True if summarization is possible now.

    allow_install=False (default): only uses what's already ready, NEVER downloads.
    allow_install=True: if Ollama or the model is missing, asks (`ask(text)
    -> bool`) and installs/downloads. Nothing is installed without that question.
    """
    if available() and _has_model():
        return True
    if not allow_install:
        return False
    if available():
        if ask and ask(
            f"Ollama is running but the model '{MODEL}' (~1.4 GB, generates summaries "
            "and keywords) has not been downloaded. Download now?"
        ):
            try:
                if subprocess.run(["ollama", "pull", MODEL]).returncode == 0:
                    return True
            except OSError:
                pass
            print(f"Run: ollama pull {MODEL}")
        return False
    if installed():
        return False

    if sys.platform != "win32" or not shutil.which("winget"):
        if ask and ask(
            "Ollama is not installed. It generates summaries and keywords "
            "(the rest of the pipeline works without it). See how to install?"
        ):
            print(MANUAL_INSTRUCTIONS)
        return False

    if not ask or not ask(
        "Ollama is not installed. It generates summaries and keywords for each "
        "document (the rest of the pipeline works without it). Install now via winget?"
    ):
        if not ask:
            print(MANUAL_INSTRUCTIONS)
        return False
    for cmd in (["winget", "install", "-e", "--id", "Ollama.Ollama"],
                ["ollama", "pull", MODEL]):
        try:
            ok = subprocess.run(cmd).returncode == 0
        except OSError:
            ok = False
        if not ok:
            print(MANUAL_INSTRUCTIONS)
            return False
    return available()


def generate(prompt: str, timeout: int = 180, max_tokens: int = 400) -> str:
    body = json.dumps({"model": MODEL, "prompt": f"{prompt}\n/no_think",
                        "stream": False, "think": False,
                        "options": {"num_predict": max_tokens, "temperature": 0.2,
                                    "repeat_penalty": 1.2}}).encode()
    req = urllib.request.Request(ENDPOINT, data=body,
                                headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = json.load(resp)["response"]
    except urllib.error.HTTPError as err:
        if err.code == 404:
            raise RuntimeError(f"model '{MODEL}' not installed — run: "
                               f"ollama pull {MODEL}") from None
        raise
    return re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
```

- [ ] **Step 2: Rewrite `biblio/version_check.py`**

```python
"""Warns if a newer version exists on GitHub. Never blocks, never fails visibly."""
import re
import urllib.request

REPO_RAW = "https://raw.githubusercontent.com/PedroHCosme/biblio/main/pyproject.toml"


def _installed_version() -> str:
    from importlib.metadata import version
    return version("biblio")


def _remote_version(timeout: float = 3) -> str | None:
    try:
        with urllib.request.urlopen(REPO_RAW, timeout=timeout) as r:
            text = r.read().decode()
        m = re.search(r'version\s*=\s*"([^"]+)"', text)
        return m.group(1) if m else None
    except Exception:
        return None


def check(warn=print) -> None:
    """Compares local vs remote. If different, warns in one line. Silent on failure."""
    try:
        local = _installed_version()
        remote = _remote_version()
        if remote and remote != local:
            warn(f"biblio {local} installed — version {remote} available. "
                 "Run `biblio update` to upgrade.")
    except Exception:
        pass
```

- [ ] **Step 3: Rewrite `biblio/shortcut.py`**

```python
"""Creates the .lnk via PowerShell and installs the skill. ponytail: no pywin32."""
import subprocess
import sys
from pathlib import Path

from biblio import skill

SCRIPT = """
$a = (New-Object -ComObject WScript.Shell).CreateShortcut('{lnk}')
$a.TargetPath = '{target}'
$a.Arguments = '-m biblio.cli gui'
$a.WorkingDirectory = '{workdir}'
$a.Description = 'biblio - document ingestion'
$a.Save()
"""


def create() -> Path | None:
    skill.install()
    if sys.platform != "win32":
        print("Shortcut is Windows-only. On other systems, run `biblio gui`.")
        return None
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    if not pythonw.exists():
        pythonw = Path(sys.executable)
    lnk = Path.home() / "Desktop" / "biblio.lnk"
    subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         SCRIPT.format(lnk=lnk, target=pythonw, workdir=Path.home())],
        check=True,
    )
    return lnk
```

- [ ] **Step 4: Verify all three files parse**

Run: `cd /c/Users/Usuario/pedrocosme/dev/fromPDFtoAgenticFriendly && /c/Users/Usuario/.conda/envs/alcoa/python.exe -c "import ast; [ast.parse(open(f'biblio/{f}').read()) for f in ('ollama.py','version_check.py','shortcut.py')]; print('OK')"`

---

### Task 4: `biblio/embed.py` + `biblio/slice.py` — intermediate modules

**Files:**
- Modify: `biblio/embed.py`, `biblio/slice.py`

#### embed.py renames

| Old | New |
|---|---|
| `MODELO` | `MODEL` |
| `PREFIXO_CONSULTA` | `QUERY_PREFIX` |
| `PREFIXO_DOC` | `DOC_PREFIX` |
| `JANELA` | `WINDOW` |
| `SOBREPOSICAO` | `OVERLAP` |
| `janelas()` | `windows()` |
| `chunks_do_documento()` | `doc_chunks()` |
| `vetorizar()` | `vectorize()` |
| `vetorizar_consulta()` | `vectorize_query()` |
| dict keys: `texto, linha_ini, linha_fim, arquivo, secao` | `text, line_start, line_end, file, section` |

- [ ] **Step 1: Rewrite `biblio/embed.py`**

```python
"""Embeddings: model and dimension decided by measurement."""
import functools
import re
from pathlib import Path

import numpy as np

MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DIM = 384
QUERY_PREFIX = ""
DOC_PREFIX = ""

WINDOW = 2000
OVERLAP = 200

_FRONTMATTER = re.compile(r"\A---\n.*?\n---\n", re.S)


@functools.lru_cache(maxsize=1)
def _model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(MODEL)


def windows(text: str, first_line: int = 1) -> list[dict]:
    """Slice by lines until the window is full. Returns text + 1-based inclusive pointer."""
    lines = text.split("\n")
    result, start = [], 0
    while start < len(lines):
        end, size = start, 0
        while end < len(lines) and (size == 0 or size + len(lines[end]) <= WINDOW):
            size += len(lines[end]) + 1
            end += 1
        block = "\n".join(lines[start:end]).strip()
        if block:
            result.append({"text": block,
                           "line_start": first_line + start,
                           "line_end": first_line + end - 1})
        if end >= len(lines):
            break
        rewind = 0
        while rewind < end - start - 1 and sum(
                len(l) + 1 for l in lines[end - rewind - 1:end]) < OVERLAP:
            rewind += 1
        start = end - rewind
    return result


def doc_chunks(doc_dir: Path) -> list[dict]:
    chunks = []
    for f in sorted(doc_dir.glob("[0-9]*.md")):
        content = f.read_text(encoding="utf-8")
        body = _FRONTMATTER.sub("", content)
        offset = content[:len(content) - len(body)].count("\n") + 1
        section = next((l for l in body.split("\n") if l.startswith("#")), f.stem)
        for win in windows(body, first_line=offset):
            chunks.append(win | {"file": f.name, "section": section.lstrip("# ")})
    return chunks


def vectorize(texts: list[str]) -> np.ndarray:
    """Vectorize corpus chunks. Document prefix, not query prefix."""
    if not texts:
        return np.empty((0, DIM), dtype="float32")
    return _model().encode([DOC_PREFIX + t for t in texts],
                           normalize_embeddings=True,
                           batch_size=16).astype("float32")


def vectorize_query(query: str) -> np.ndarray:
    return _model().encode([QUERY_PREFIX + query], normalize_embeddings=True,
                           batch_size=1).astype("float32")[0]
```

#### slice.py renames

| Old | New |
|---|---|
| `PISO` | `FLOOR` |
| `TETO` | `CEILING` |
| `Fatia` | `Slice` |
| `_Bruta` | `_RawSection` |
| fields: `ordem, secao, nivel, texto, pagina_ini, pagina_fim, pai, sufixo, nome` | `order, section, level, text, page_start, page_end, parent, suffix, name` |
| `fatiar()` | `slice_doc()` |
| param `com_paginas` | `with_pages` |

- [ ] **Step 2: Rewrite `biblio/slice.py`**

```python
"""Cuts normalized markdown into slices by heading, with floor and ceiling."""
import re
from dataclasses import dataclass, field

from biblio.paths import slug

FLOOR = 400
CEILING = 8000

_HEADING = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
_MARKER = re.compile(r"^<!-- pag (\d+) -->$")


@dataclass
class Slice:
    order: int
    section: str
    level: int
    text: str
    page_start: int | None
    page_end: int | None
    parent: str | None = None
    suffix: str = ""

    @property
    def name(self) -> str:
        return f"{self.order:02d}-{slug(self.section)}{self.suffix}.md"


@dataclass
class _RawSection:
    section: str = ""
    level: int = 0
    lines: list[str] = field(default_factory=list)
    pages: list[int] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(self.lines).strip()


def _split_by_heading(markdown: str) -> list[_RawSection]:
    """One raw section per heading; content before the first heading is the preamble."""
    sections = [_RawSection(section="", level=0)]
    page = 1
    for line in markdown.split("\n"):
        if m := _MARKER.match(line.strip()):
            page = int(m.group(1))
            sections[-1].pages.append(page)
            continue
        if m := _HEADING.match(line):
            title, level = m.group(2), len(m.group(1))
            if slug(sections[-1].section) == slug(title) and sections[-1].level == level:
                sections[-1].pages.append(page)
                continue
            sections.append(_RawSection(section=title, level=level, pages=[page]))
        sections[-1].lines.append(line)
    if not sections[0].text:
        sections.pop(0)
    return sections


def _apply_floor(sections: list[_RawSection]) -> list[_RawSection]:
    """Short section merges into the next; if it's the last, merges into the previous."""
    merged: list[_RawSection] = []
    pending: _RawSection | None = None
    for sec in sections:
        if pending:
            sec = _RawSection(
                section=pending.section or sec.section,
                level=pending.level or sec.level,
                lines=pending.lines + sec.lines,
                pages=pending.pages + sec.pages,
            )
            pending = None
        if len(sec.text) < FLOOR:
            pending = sec
            continue
        merged.append(sec)
    if pending:
        if merged:
            merged[-1].lines += pending.lines
            merged[-1].pages += pending.pages
        else:
            merged.append(pending)
    return merged


def _split_at_ceiling(text: str) -> list[str]:
    if len(text) <= CEILING:
        return [text]
    chunks, current = [], ""
    for paragraph in text.split("\n\n"):
        if current and len(current) + len(paragraph) + 2 > CEILING:
            chunks.append(current)
            current = paragraph
        else:
            current = f"{current}\n\n{paragraph}" if current else paragraph
    if current:
        chunks.append(current)
    return chunks


def slice_doc(markdown: str, with_pages: bool = True) -> list[Slice]:
    """with_pages=False for sources without pages (.md, .txt): frontmatter omits the field."""
    raw = _apply_floor(_split_by_heading(markdown))
    no_heading = not any(s.level for s in raw)

    slices: list[Slice] = []
    ancestors: dict[int, str] = {}
    for idx, section in enumerate(raw, start=1):
        pages = section.pages or [1]
        pieces = _split_at_ceiling(section.text)
        parent_name = next(
            (name for level, name in sorted(ancestors.items(), reverse=True)
             if level < section.level),
            None,
        )
        for i, piece in enumerate(pieces):
            slices.append(Slice(
                order=len(slices) + 1 if no_heading else idx,
                section="part" if no_heading else (section.section or "preamble"),
                level=section.level,
                text=piece,
                page_start=min(pages) if with_pages else None,
                page_end=max(pages) if with_pages else None,
                parent=parent_name,
                suffix="" if no_heading or len(pieces) == 1 else f"-{chr(97 + i)}",
            ))
        if section.level:
            ancestors[section.level] = slices[-1].name
            for lvl in [n for n in ancestors if n > section.level]:
                del ancestors[lvl]
    return slices
```

- [ ] **Step 3: Verify both files parse**

Run: `cd /c/Users/Usuario/pedrocosme/dev/fromPDFtoAgenticFriendly && /c/Users/Usuario/.conda/envs/alcoa/python.exe -c "import ast; [ast.parse(open(f'biblio/{f}').read()) for f in ('embed.py','slice.py')]; print('OK')"`

---

### Task 5: `biblio/db.py` + `biblio/convert.py` + `biblio/summarize.py` — SQL schema + intermediate

**Files:**
- Modify: `biblio/db.py`, `biblio/convert.py`, `biblio/summarize.py`

#### db.py renames

| Old | New |
|---|---|
| SQL columns: `chave, valor, arquivo, secao, linha_ini, linha_fim, texto, vetor` | `key, value, file, section, line_start, line_end, text, vector` |
| config key `'modelo'` | `'model'` |
| `conectar()` | `connect()` |
| `substituir_documento()` | `replace_document()` |
| `buscar_fts()` | `search_fts()` |
| `buscar_vetorial()` | `search_vector()` |
| `detalhes()` | `details()` |

**Important:** Add `_migrate_schema()` to detect old Portuguese column names and drop tables, since `CREATE TABLE IF NOT EXISTS` won't recreate existing tables. The meta.yaml migration forces reindexation, which repopulates the DB.

- [ ] **Step 1: Rewrite `biblio/db.py`**

```python
"""One SQLite file per bibliotheca: FTS5 + vectors.

ponytail: brute-force vector search in numpy. For the measured corpus size
it's instant and avoids a native extension dependency.
"""
import sqlite3
from pathlib import Path

import numpy as np

from biblio.embed import DIM, MODEL

DB_FILE = "biblio.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS chunks (
  id         INTEGER PRIMARY KEY,
  doc        TEXT NOT NULL,
  file       TEXT NOT NULL,
  section    TEXT,
  line_start INTEGER NOT NULL,
  line_end   INTEGER NOT NULL,
  text       TEXT NOT NULL,
  vector     BLOB
);
CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(doc);
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
  text, section, content='chunks', content_rowid='id',
  tokenize="unicode61 remove_diacritics 2"
);
"""


def _migrate_schema(con: sqlite3.Connection) -> None:
    """Drop old Portuguese-column tables so they're recreated with new names."""
    try:
        con.execute("SELECT chave FROM config LIMIT 1")
        con.executescript("""
            DROP TABLE IF EXISTS chunks_fts;
            DROP TABLE IF EXISTS chunks;
            DROP TABLE IF EXISTS config;
        """)
    except sqlite3.OperationalError:
        pass


def connect(bibliotheca: Path) -> sqlite3.Connection:
    con = sqlite3.connect(bibliotheca / DB_FILE)
    con.row_factory = sqlite3.Row
    _migrate_schema(con)
    con.executescript(SCHEMA)
    _check_model(con)
    return con


def _check_model(con: sqlite3.Connection) -> None:
    """Vectors from one model compared with another aren't bad results, they're noise."""
    with con:
        saved = con.execute(
            "SELECT value FROM config WHERE key = 'model'").fetchone()
        if saved is None:
            con.execute("INSERT INTO config VALUES('model', ?)", (MODEL,))
        elif saved[0] != MODEL:
            raise SystemExit(
                f"This bibliotheca was indexed with '{saved[0]}', and this biblio uses "
                f"'{MODEL}'. The vectors are not comparable.\n"
                f"Reindex with: biblio add <source> --force")


def replace_document(con: sqlite3.Connection, doc: str, chunks: list[dict],
                     vectors: np.ndarray) -> None:
    """Deletes and reinserts the entire document. Reprocessing never duplicates."""
    with con:
        old = [tuple(r) for r in con.execute(
            "SELECT id, text, section FROM chunks WHERE doc = ?", (doc,))]
        con.executemany("INSERT INTO chunks_fts(chunks_fts, rowid, text, section) "
                        "VALUES('delete', ?, ?, ?)", old)
        con.execute("DELETE FROM chunks WHERE doc = ?", (doc,))
        for chunk, vector in zip(chunks, vectors):
            cursor = con.execute(
                "INSERT INTO chunks(doc, file, section, line_start, line_end, text, vector)"
                " VALUES(?,?,?,?,?,?,?)",
                (doc, chunk["file"], chunk["section"], chunk["line_start"],
                 chunk["line_end"], chunk["text"],
                 np.asarray(vector, dtype="float32").tobytes()),
            )
            con.execute("INSERT INTO chunks_fts(rowid, text, section) VALUES(?,?,?)",
                        (cursor.lastrowid, chunk["text"], chunk["section"]))


def search_fts(con: sqlite3.Connection, query: str, k: int,
               doc: str | None = None) -> list[int]:
    terms = " OR ".join(f'"{t}"' for t in query.split() if t)
    if not terms:
        return []
    sql = ("SELECT c.id FROM chunks_fts f JOIN chunks c ON c.id = f.rowid "
           "WHERE chunks_fts MATCH ?")
    params: list = [terms]
    if doc:
        sql += " AND c.doc = ?"
        params.append(doc)
    sql += " ORDER BY bm25(chunks_fts) LIMIT ?"
    params.append(k)
    return [row["id"] for row in con.execute(sql, params)]


def search_vector(con: sqlite3.Connection, query: np.ndarray, k: int,
                  doc: str | None = None) -> list[int]:
    sql = "SELECT id, vector FROM chunks WHERE vector IS NOT NULL"
    params: list = []
    if doc:
        sql += " AND doc = ?"
        params.append(doc)
    rows = con.execute(sql, params).fetchall()
    if not rows:
        return []
    ids = np.array([row["id"] for row in rows])
    matrix = np.frombuffer(b"".join(row["vector"] for row in rows),
                           dtype="float32").reshape(len(ids), DIM)
    scores = matrix @ np.asarray(query, dtype="float32")
    best = np.argsort(scores)[::-1][:k]
    return [int(ids[i]) for i in best]


def details(con: sqlite3.Connection, ids: list[int]) -> dict[int, sqlite3.Row]:
    if not ids:
        return {}
    placeholders = ",".join("?" * len(ids))
    return {row["id"]: row for row in con.execute(
        f"SELECT id, doc, file, section, line_start, line_end FROM chunks "
        f"WHERE id IN ({placeholders})", ids)}
```

#### convert.py renames

| Old | New |
|---|---|
| `converter()` | `convert()` |
| internal variables | English |
| `ARQUIVO` constant renamed in db.py from `ARQUIVO` to `DB_FILE` | update reference |

- [ ] **Step 2: Rewrite `biblio/convert.py`**

```python
"""Runs the right converter per page and returns a single markdown with markers."""
from pathlib import Path

import pymupdf
import pymupdf4llm

MARKER = "<!-- pag {} -->"


def _convert_native(pdf_path: Path, pages: list[int]) -> dict[int, str]:
    if not pages:
        return {}
    blocks = pymupdf4llm.to_markdown(
        str(pdf_path), pages=[p - 1 for p in pages], page_chunks=True
    )
    return {b["metadata"]["page_number"]: b["text"] for b in blocks}


def _convert_with_docling(pdf_path: Path, pages: list[int], ocr: bool,
                          device: str, warn=None, label: str = "") -> dict[int, str]:
    """Docling doesn't accept page subsets, so each page becomes a one-page PDF."""
    if not pages:
        return {}
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    options = PdfPipelineOptions()
    options.do_ocr = ocr
    options.do_table_structure = True
    if device != "auto":
        options.accelerator_options.device = device

    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)}
    )

    output: dict[int, str] = {}
    total = len(pages)
    with pymupdf.open(pdf_path) as source:
        for i, number in enumerate(pages, 1):
            if warn:
                warn(f"  {label} page {number} ({i}/{total})")
            excerpt = pymupdf.open()
            excerpt.insert_pdf(source, from_page=number - 1, to_page=number - 1)
            tmp = pdf_path.parent / f".{pdf_path.stem}-p{number}.pdf"
            excerpt.save(tmp)
            excerpt.close()
            try:
                output[number] = converter.convert(tmp).document.export_to_markdown()
            finally:
                tmp.unlink(missing_ok=True)
    return output


def convert(pdf_path: Path, route: dict[str, list[int]], device: str = "auto",
            warn=None, fast: bool = False) -> str:
    """Markdown of the entire document, pages in order, each preceded by a marker.

    fast=True: skips Docling, uses pymupdf4llm for everything. Fast, but scanned
    pages (OCR) come out empty or garbled.
    """
    if fast:
        all_pages = sorted(route["native"] + route["complex"] + route["ocr"])
        pages = _convert_native(pdf_path, all_pages)
    else:
        pages = {}
        pages |= _convert_native(pdf_path, route["native"])
        pages |= _convert_with_docling(pdf_path, route["complex"], ocr=False, device=device,
                                       warn=warn, label="docling")
        pages |= _convert_with_docling(pdf_path, route["ocr"], ocr=True, device=device,
                                       warn=warn, label="ocr")

    parts = []
    for number in sorted(pages):
        parts.append(MARKER.format(number))
        parts.append(pages[number].strip())
    return "\n\n".join(parts) + "\n"
```

#### summarize.py renames

| Old | New |
|---|---|
| `MAX_AMOSTRA` | `MAX_SAMPLE` |
| `resumir()` | `summarize()` |
| internal functions | English |
| **PROMPT stays in Portuguese** | No change to prompt text |

- [ ] **Step 3: Rewrite `biblio/summarize.py`**

```python
"""One summary per document — never per chunk. Runs once, costs zero after."""
import re
from pathlib import Path

from biblio import ollama

MAX_SAMPLE = 6_000

# Prompt stays in Portuguese (user decision). RESUMO:/TERMOS: markers and parser stay.
PROMPT = """Voce recebe o inicio de um documento. Responda **no idioma do documento**, \
exatamente neste formato, sem preambulo:

RESUMO: <uma frase dizendo o que o documento e e para que serve>
TERMOS: <8 a 12 termos de busca do assunto, separados por virgula, sem numeracao. \
Use as palavras como aparecem no documento, sem traduzir>

Documento:
{amostra}"""


_FRONTMATTER = re.compile(r"\A---\r?\n.*?\r?\n---\r?\n", re.S)
_TOC_LINE = re.compile(r"^\s*(?:[-*+]\s+)?(?:\[\[|\[[^\]]*\]\(#|\d+(?:\.\d+)*\s|.{0,50}\.{3,}\s*\d+\s*$)")
_ALIASES_LINE = re.compile(r"^\*[^*]+\*$")


def _is_prose(line: str) -> bool:
    stripped = line.strip()
    if not stripped or stripped in ("---", "***") or stripped.startswith(
            ("#", "|", "```", "<!--")):
        return False
    if _ALIASES_LINE.match(stripped):
        return False
    return not _TOC_LINE.match(stripped)


def _sample(doc_dir: Path) -> str:
    files = sorted(doc_dir.glob("[0-9]*.md"))
    parts: list[str] = []
    total = 0
    for f in files:
        body = _FRONTMATTER.sub("", f.read_text(encoding="utf-8"))
        for line in body.splitlines():
            if line.startswith("#") or _is_prose(line):
                parts.append(line)
                total += len(line) + 1
        if total > MAX_SAMPLE:
            break
    text = "\n".join(parts).strip()[:MAX_SAMPLE]
    if len(text) >= 200:
        return text
    return _FRONTMATTER.sub("", "".join(
        f.read_text(encoding="utf-8") for f in files))[:MAX_SAMPLE]


def _extract(response: str) -> tuple[str, list[str]]:
    text = response.replace("*", "").strip()
    cut = re.search(r"(?i)\btermos?\s*:", text)
    before = text[:cut.start()] if cut else text
    after = text[cut.end():] if cut else ""

    m = re.search(r"(?i)\bresumo\s*:\s*(.+)", before, re.S)
    summary = (m.group(1) if m else before).strip().split("\n")[0].strip()

    after = after.split("\n\n")[0]
    terms = [t.strip(" .;\n\t-") for t in re.split(r"[,\n]", after)]
    return summary, [t for t in terms if t and len(t) <= 40][:15]


def summarize(doc_dir: Path) -> tuple[str, list[str]]:
    """Writes `_resumo.md` and returns (summary, terms). Raises if Ollama fails."""
    summary, terms = _extract(ollama.generate(PROMPT.format(amostra=_sample(doc_dir))))
    (doc_dir / "_resumo.md").write_text(
        f"{summary}\n\n**Termos:** {', '.join(terms)}\n", encoding="utf-8"
    )
    return summary, terms
```

- [ ] **Step 4: Verify all three files parse**

Run: `cd /c/Users/Usuario/pedrocosme/dev/fromPDFtoAgenticFriendly && /c/Users/Usuario/.conda/envs/alcoa/python.exe -c "import ast; [ast.parse(open(f'biblio/{f}').read()) for f in ('db.py','convert.py','summarize.py')]; print('OK')"`

---

### Task 6: `biblio/search.py` — hybrid search

**Files:**
- Modify: `biblio/search.py`

| Old | New |
|---|---|
| `buscar()` | `search()` |
| `formatar()` | `format_results()` |
| param `consulta` | `query` |
| param `contexto` | `context` |
| context values `"secao"`, `"janela"` | `"section"`, `"window"` |
| output key `"caminho"` | `"path"` |
| output key `"secao"` (stays) | `"section"` (already matches) |
| cross-module refs | Updated to new names |

- [ ] **Step 1: Rewrite `biblio/search.py`**

```python
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
```

- [ ] **Step 2: Verify**

Run: `cd /c/Users/Usuario/pedrocosme/dev/fromPDFtoAgenticFriendly && /c/Users/Usuario/.conda/envs/alcoa/python.exe -c "import ast; ast.parse(open('biblio/search.py').read()); print('OK')"`

---

### Task 7: `biblio/index.py` + `biblio/skill.py` — orchestration + English text

**Files:**
- Modify: `biblio/index.py`, `biblio/skill.py`

These files contain the most user-facing text. All Portuguese text translates to English.

- [ ] **Step 1: Rewrite `biblio/index.py`**

```python
"""Generates INDEX.md and CLAUDE.md from the bibliotheca on disk. Never reprocesses originals."""
from pathlib import Path

from biblio import meta, ollama, skill, summarize
from biblio.paths import root, register

HEADER = """# Bibliotheca

Index for `grep`, not for reading. One block per document; the **Terms** line is
the fallback when semantic search misses.

Use `biblio search "<query>"` first. Never read this entire file.

Can't run `biblio search`? Then this index is the entry point: find the document
block by its **Terms** line and read only the sections the block names.

"""


def _provenance(data: dict) -> str:
    """Source that was already text has no pages or OCR: don't invent either."""
    if not (pages := data.get("pages")):
        return data.get("format", "text")
    route = data.get("route", {})
    nature = f"{route['ocr']} OCR pages" if route.get("ocr") else "native text"
    return f"{pages} pages, {nature}"


def _block(folder: Path, data: dict) -> str:
    summary = data.get("summary")
    if not summary or summary == "pending":
        summary = "no summary"
    lines = [
        f"## {folder.name}",
        f"{summary} {_provenance(data)}.",
    ]
    if data.get("failed"):
        lines.append(f"**FAILED:** {data['failed']}")
    if data.get("quality") == "low":
        lines.append("**WARNING:** low-quality OCR, check against the original.")
    if terms := data.get("terms"):
        lines.append(f"**Terms:** {', '.join(terms)}")
    sections = sorted(p.stem for p in folder.glob("[0-9]*.md"))
    if sections:
        show = sections[:8] + ([f"... (+{len(sections) - 8})"] if len(sections) > 8 else [])
        lines.append(f"**Sections:** {' · '.join(show)}")
    lines.append(f"`{folder.name}/`")
    return "\n".join(lines) + "\n"


def generate(output=None, summary: str = "auto", ask=None, warn=print) -> Path:
    """`summary`: 'auto' (default) fills pending summaries IF Ollama is ready;
    'yes' asks and installs if missing; 'no' only regenerates INDEX/CLAUDE.
    """
    bibliotheca = root(output)
    bibliotheca.mkdir(parents=True, exist_ok=True)
    summarize_pending = ollama.wants_summary(summary, ask, warn)
    blocks = []
    for folder in sorted(p for p in bibliotheca.iterdir() if p.is_dir()):
        data = meta.read(folder)
        if not data:
            continue
        if summarize_pending and data.get("summary") == "pending":
            try:
                s, terms = summarize.summarize(folder)
                data |= {"summary": s, "terms": terms}
                meta.write(folder, data)
                warn(f"{folder.name}: summary generated")
            except Exception as err:
                warn(f"{folder.name}: summary still pending ({err})")
        blocks.append(_block(folder, data))

    if blocks:
        register(bibliotheca)

    (bibliotheca / "CLAUDE.md").write_text(skill.claude_md_text(), encoding="utf-8")
    dest = bibliotheca / "INDEX.md"
    dest.write_text(HEADER + "\n".join(blocks), encoding="utf-8")
    return dest
```

- [ ] **Step 2: Rewrite `biblio/skill.py`**

```python
"""The text that teaches the agent, and its installation.

The skill lives in ~/.claude/skills and covers Claude Code without the user pointing anything.
The CLAUDE.md lives inside the folder and covers a bibliotheca copied to another machine,
Claude Desktop, Cowork, and ChatGPT. Same protocol, two scopes.
"""
import sys
from pathlib import Path

from biblio.paths import known_bibliothecas

DEST = Path.home() / ".claude" / "skills" / "bibliotheca"
MAX_NAMES = 8


def _executable() -> str:
    """Absolute path to `biblio`, so the skill doesn't depend on PATH."""
    for candidate in (Path(sys.executable).parent / "Scripts" / "biblio.exe",
                      Path(sys.executable).with_name("biblio")):
        if candidate.exists():
            return f'"{candidate}"'
    return "biblio"


PROTOCOL = """\
## Protocol

**1. Always start with search.**

```bash
{command} search "<the question rewritten in domain terms>"{scope}
```

Rewrite before searching. "How much rebar do I need to anchor?" searches poorly;
"anchorage length passive reinforcement" searches well.

Each result is one line: absolute path, line range, score, heading.

```
C:\\\\Users\\\\...\\\\biblio\\\\nbr-6118\\\\09-ancoragem.md:1-84  0.032  9.4 Comprimento de ancoragem
```

**Never the content** — that's intentional.

**2. Read the range the search returned, using `offset` and `limit`.**

The range is the **entire section** that matched (delimited by heading, at most
~2000 tokens). For `...09-ancoragem.md:112-195`, use `Read` with `offset=112` and
`limit=84`.

**`limit` is the number of lines — `end - start + 1` — not the final line.**
For `:19-36`, it's `offset=19` and `limit=18`.

Read only the returned range — not neighboring files. If you still need context,
read the 2nd result too. If nothing answers, search again with different terms.
(`--context window` returns only the exact matched chunk, shorter.)

**3. Empty search? Go to the index terms.**

```bash
grep -A4 -i "<term>" <bibliotheca>/INDEX.md
```

The `**Terms:**` line in each block is the safety net for exact identifiers
("NBR 6118", "9.4.2", part name) that semantic search misses.

**4. Never read the entire `INDEX.md`.** Two hundred documents yield 40k tokens.
It was written for `grep`, not for reading.

## Other commands

| Command | Purpose |
|---|---|
| `biblio add <folder>` | Ingest. **Does not generate summaries by default** — ask the user and pass `--summary` only if they want it (this may download ~1.4 GB) |
| `biblio search "x" --doc <name>` | Restrict to one document |
| `biblio search "x" --lib <path>` | Restrict to one bibliotheca |
| `biblio search "x" --context window` | Minimal chunk instead of full section |
| `biblio libs` | List registered bibliothecas |
| `biblio status` | What was ingested, what failed, what's pending |

## Cautions

- Index block with **WARNING** about low-quality OCR: the text may be corrupted.
  Tell the user before citing numbers from it.
- Every file starts with frontmatter (`doc`, `section`, `parent`, and `pages` when
  the source was PDF). Use `pages` to cite the original page.
- The bibliotheca doesn't store the original file; `_meta.yaml` stores its path.
"""

SKILL_HEADER = """# Document bibliotheca

Local indexed corpus managed by `biblio`. Too large to read: the protocol below
exists to find the right paragraph without loading the corpus.

The path below is complete on purpose: use it exactly as-is, in any shell.
Do not shorten to `biblio` — not every shell has the Windows PATH.
"""


def _description() -> str:
    names = [Path(c).name for c in known_bibliothecas()[:MAX_NAMES]]
    which = f" (bibliothecas: {', '.join(names)})" if names else ""
    return (f"Search the user's document corpus{which}. Use whenever the "
            "question can be answered by a corpus document instead of "
            "general knowledge.")


def skill_text() -> str:
    body = SKILL_HEADER + "\n" + PROTOCOL.format(command=_executable(), scope="")
    return f"---\nname: bibliotheca\ndescription: {_description()}\n---\n\n{body}"


def claude_md_text() -> str:
    return f"""# Bibliotheca biblio

This folder is an indexed document corpus. **Do not scan it** — it's hundreds of
thousands of tokens. Use `biblio search`, which returns pointers.

In the commands below, `--lib` takes **the path to this folder** — the same one
you read this file from. Its name also works, if already known on this machine
(`biblio libs`). Using a folder once makes it known.

If `biblio` gives "command not found", the executable exists but isn't in this
shell's PATH. Try another shell (on Windows, PowerShell) before concluding the
tool is not installed — and **do not** fall back to scanning the folder.

{PROTOCOL.format(command='biblio', scope=' --lib "<path to this folder>"')}"""


def install(warn=print) -> Path:
    """Overwrites the installed skill. Idempotent, cheap, runs on every ingestion."""
    DEST.mkdir(parents=True, exist_ok=True)
    target = DEST / "SKILL.md"
    text = skill_text()
    if not target.exists() or target.read_text(encoding="utf-8") != text:
        target.write_text(text, encoding="utf-8")
        warn(f"skill installed at {target}")
    return target
```

- [ ] **Step 3: Verify both files parse**

Run: `cd /c/Users/Usuario/pedrocosme/dev/fromPDFtoAgenticFriendly && /c/Users/Usuario/.conda/envs/alcoa/python.exe -c "import ast; [ast.parse(open(f'biblio/{f}').read()) for f in ('index.py','skill.py')]; print('OK')"`

---

### Task 8: `biblio/pipeline.py` — central orchestrator

**Files:**
- Modify: `biblio/pipeline.py`

| Old | New |
|---|---|
| `adicionar()` | `ingest()` |
| all cross-module calls | Updated to new names |
| counter keys `"pulado"`, `"falhou"` | `"skipped"`, `"failed"` |
| frontmatter keys `secao, paginas, pai` | `section, pages, parent` |
| progress messages | English |
| `resumo` param | `summary` |
| `saida` param | `output` |

- [ ] **Step 1: Rewrite `biblio/pipeline.py`**

```python
"""ingest(): the single entry point. CLI and GUI are shells over it."""
import re
from pathlib import Path

import yaml

from biblio import db, embed, meta, ollama, summarize
from biblio.convert import convert
from biblio.normalize import normalize
from biblio.paths import root, register, slug
from biblio.slice import slice_doc
from biblio.triage import triage

EXTENSIONS = (".pdf", ".md", ".txt")


def _files(target: Path) -> list[Path]:
    if target.is_dir():
        return sorted(p for p in target.rglob("*") if p.suffix.lower() in EXTENSIONS)
    return [target]


def _frontmatter(s, doc: str) -> str:
    fields = {"doc": doc, "section": s.section}
    if s.page_start is not None:
        fields["pages"] = [s.page_start, s.page_end]
    fields["parent"] = s.parent
    return "---\n" + yaml.safe_dump(fields, allow_unicode=True, sort_keys=False) + "---\n\n"


_SOURCE_FRONTMATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.S)


def _strip_source_frontmatter(text: str) -> str:
    """Obsidian vault: every .md already has its own YAML frontmatter."""
    m = _SOURCE_FRONTMATTER.match(text)
    if not m:
        return text
    try:
        data = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        data = {}
    terms = data.get("aliases", []) + data.get("tags", []) if isinstance(data, dict) else []
    line = f"*{', '.join(map(str, terms))}*\n\n" if terms else ""
    return line + text[m.end():]


def _get_text(path: Path, device: str, warn, name: str,
              fast: bool = False) -> tuple[str, dict]:
    """(raw markdown, route). Input that's already text skips triage and conversion."""
    if path.suffix.lower() != ".pdf":
        warn(f"{name}: already text, skipping conversion")
        raw = path.read_text(encoding="utf-8", errors="replace")
        return _strip_source_frontmatter(raw), {}
    warn(f"{name}: triaging")
    route = triage(path)
    n_nat, n_cplx, n_ocr = len(route["native"]), len(route["complex"]), len(route["ocr"])
    parts = []
    if n_nat:
        parts.append(f"{n_nat} native")
    if n_cplx:
        parts.append(f"{n_cplx} with tables")
    if n_ocr:
        parts.append(f"{n_ocr} OCR (~{n_ocr * 30}s on CPU)")
    warn(f"{name}: {' + '.join(parts) or '0 pages'}"
         + (" [fast: no OCR]" if fast else ""))
    return convert(path, route, device=device, warn=warn, fast=fast), route


def _process_one(path: Path, bibliotheca: Path, device: str, force: bool,
                 warn, summarize_with_ollama: bool = False,
                 max_size_mb: float | None = None, fast: bool = False) -> str:
    name = slug(path.stem)
    folder = bibliotheca / name
    size_mb = path.stat().st_size / (1024 * 1024)
    if max_size_mb is not None and size_mb > max_size_mb:
        warn(f"{name}: {size_mb:.1f}MB > limit of {max_size_mb}MB, skipping")
        return "skipped"

    digest = meta.hash_file(path)

    if not force and meta.already_processed(folder, digest):
        warn(f"{name}: unchanged, skipping")
        return "skipped"

    prev = meta.read(folder).get("source")
    if prev and prev != str(path.resolve()):
        warn(f"{name}: WARNING — same name as {Path(prev).name}, overwriting")

    try:
        raw, route = _get_text(path, device, warn, name, fast=fast)
    except Exception as err:
        warn(f"{name}: FAILED ({err})")
        meta.write(folder, {"source": str(path.resolve()), "hash": digest,
                            "failed": str(err)[:120]})
        return "failed"

    warn(f"{name}: slicing")
    slices = slice_doc(normalize(raw), with_pages=bool(route))

    for old in folder.glob("[0-9]*.md"):
        old.unlink()
    folder.mkdir(parents=True, exist_ok=True)
    for s in slices:
        (folder / s.name).write_text(_frontmatter(s, name) + s.text + "\n",
                                     encoding="utf-8")

    record = meta.new_record(path, digest, route)
    record["slices"] = len(slices)

    warn(f"{name}: indexing")
    chunks = embed.doc_chunks(folder)
    con = db.connect(bibliotheca)
    try:
        db.replace_document(con, name, chunks,
                            embed.vectorize([c["text"] for c in chunks]))
    finally:
        con.close()
    record["chunks"] = len(chunks)

    if summarize_with_ollama:
        try:
            s, terms = summarize.summarize(folder)
            record |= {"summary": s, "terms": terms}
        except Exception as err:
            warn(f"{name}: summary pending ({err})")
    meta.write(folder, record)
    warn(f"{name}: {len(slices)} slices")
    return "ok"


def ingest(target: Path | str, output: Path | str | None = None, device: str = "auto",
           force: bool = False, warn=print, ask=None,
           summary: str = "auto", max_size_mb: float | None = None,
           fast: bool = False) -> dict[str, int]:
    """Processes a file (.pdf/.md/.txt) or a folder.

    `warn` is the only progress channel: the GUI passes its own.
    `summary`: 'auto' uses Ollama IF already ready; 'yes' asks and installs;
    'no' never summarizes.
    `max_size_mb`: skips files larger than this (None = no limit).
    `fast`: skips Docling/OCR, uses pymupdf4llm for everything.
    """
    bibliotheca = root(output)
    bibliotheca.mkdir(parents=True, exist_ok=True)
    summarize_with_ollama = ollama.wants_summary(summary, ask, warn)

    count = {"ok": 0, "skipped": 0, "failed": 0}
    for f in _files(Path(target)):
        try:
            count[_process_one(f, bibliotheca, device, force, warn,
                               summarize_with_ollama,
                               max_size_mb=max_size_mb, fast=fast)] += 1
        except Exception as err:
            warn(f"{f.name}: FAILED ({err})")
            count["failed"] += 1

    if count["ok"] or count["skipped"]:
        register(bibliotheca)
    return count
```

- [ ] **Step 2: Verify**

Run: `cd /c/Users/Usuario/pedrocosme/dev/fromPDFtoAgenticFriendly && /c/Users/Usuario/.conda/envs/alcoa/python.exe -c "import ast; ast.parse(open('biblio/pipeline.py').read()); print('OK')"`

---

### Task 9: `biblio/cli.py` + `biblio/gui.py` — interfaces

**Files:**
- Modify: `biblio/cli.py`, `biblio/gui.py`

All help text, messages, labels → English. All cross-module references → new names.

- [ ] **Step 1: Rewrite `biblio/cli.py`**

```python
"""argparse and nothing else. All logic lives in the modules; only parsing here."""
import argparse
import json
import sys
from pathlib import Path

from biblio import index, meta, pipeline, search, skill
from biblio.paths import known_bibliothecas, root


def _confirm(text: str) -> bool:
    return input(f"{text} [y/N] ").strip().lower() in ("y", "yes", "s", "sim")


def _status(args) -> int:
    bibliotheca = root(args.out)
    if not bibliotheca.exists():
        print(f"empty bibliotheca: {bibliotheca}")
        return 0
    for folder in sorted(p for p in bibliotheca.iterdir() if p.is_dir()):
        data = meta.read(folder)
        if not data:
            continue
        state = data.get("failed") or (
            "summary pending" if data.get("summary") == "pending" else "ok")
        source = f"{data['pages']} pages" if data.get("pages") else data.get(
            "format", "?")
        print(f"{folder.name:<45} {source:>8}  "
              f"{data.get('slices','?'):>3} slices  {state}")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="biblio",
                                description="Document memory layer for agents")
    p.add_argument("--out", help="bibliotheca folder (default: ~/biblio)")
    sub = p.add_subparsers(dest="command", required=True)

    a = sub.add_parser("add", help="ingest .pdf, .md or .txt — file or folder")
    a.add_argument("target")
    a.add_argument("--device", default="auto", help="auto | cpu | cuda")
    a.add_argument("--force", action="store_true", help="reprocess even without changes")
    a.add_argument("--summary", dest="summary_mode", action="store_const", const="yes",
                   default="auto", help="generate summary/terms per document; downloads "
                   "Ollama+qwen if needed (asks first)")
    a.add_argument("--no-summary", dest="summary_mode", action="store_const", const="no",
                   help="never generate summary/terms, even with Ollama available")
    a.add_argument("--max-size", type=float, default=None, metavar="MB",
                   help="skip files larger than N megabytes (e.g. --max-size 10)")
    a.add_argument("--fast", action="store_true",
                   help="skip OCR (Docling), use only native extraction — fast but "
                   "scanned pages come out empty")

    b = sub.add_parser("search", help="search and return pointers")
    b.add_argument("query")
    b.add_argument("--top", type=int, default=5)
    b.add_argument("--doc", help="restrict to one document")
    b.add_argument("--lib", help="restrict to one bibliotheca: path or name "
                                 "(default: all known)")
    b.add_argument("--context", choices=("section", "window"), default="section",
                   help="section: entire slice (default); window: only the matched chunk")
    b.add_argument("--json", action="store_true")

    i = sub.add_parser("index", help="regenerate INDEX.md and CLAUDE.md without reprocessing")
    i.add_argument("--summary", dest="summary_mode", action="store_const", const="yes",
                   default="auto", help="fill pending summaries; installs "
                   "Ollama+qwen if needed (asks first)")
    i.add_argument("--no-summary", dest="summary_mode", action="store_const", const="no",
                   help="only regenerate INDEX.md/CLAUDE.md, without touching summaries")
    sub.add_parser("status", help="what was ingested, what failed, what's pending")
    sub.add_parser("libs", help="registered bibliothecas")
    sub.add_parser("skill", help="install the Claude Code skill (without creating shortcut)")
    sub.add_parser("gui", help="launch the localhost interface")
    sub.add_parser("shortcut", help="create the desktop shortcut")
    sub.add_parser("version", help="show installed version")
    sub.add_parser("update", help="update to the latest GitHub version")

    args = p.parse_args(argv)

    if args.command in ("add", "gui", "index"):
        from biblio.version_check import check
        check()

    if args.command == "add":
        count = pipeline.ingest(Path(args.target), output=args.out, device=args.device,
                                force=args.force, ask=_confirm,
                                summary=args.summary_mode, max_size_mb=args.max_size,
                                fast=args.fast)
        index.generate(output=args.out, summary="no")
        if count["ok"]:
            skill.install()
        print(f"\n{count['ok']} processed, {count['skipped']} unchanged, "
              f"{count['failed']} failed")
        return 1 if count["failed"] else 0

    if args.command == "search":
        results = search.search(args.query, output=args.lib or args.out,
                                top=args.top, doc=args.doc, context=args.context)
        print(json.dumps(results, ensure_ascii=False) if args.json
              else search.format_results(results))
        return 0

    if args.command == "index":
        dest = index.generate(output=args.out, summary=args.summary_mode, ask=_confirm)
        skill.install()
        print(dest)
        return 0

    if args.command == "status":
        return _status(args)

    if args.command == "libs":
        for path in known_bibliothecas() or ["(none; run `biblio add`)"]:
            print(path)
        return 0

    if args.command == "skill":
        print(skill.install())
        return 0

    if args.command == "gui":
        from biblio.gui import launch
        launch(output=args.out)
        return 0

    if args.command == "shortcut":
        from biblio.shortcut import create
        if lnk := create():
            print(lnk)
        return 0

    if args.command == "version":
        from importlib.metadata import version
        print(f"biblio {version('biblio')}")
        return 0

    if args.command == "update":
        import subprocess
        url = "git+https://github.com/PedroHCosme/biblio.git"
        print(f"Updating from {url} ...")
        return subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", url]).returncode

    return 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Rewrite `biblio/gui.py`**

```python
"""Ingestion panel. Calls pipeline.ingest() and shows its progress.

No search, no reading, no chat.
"""
from pathlib import Path

import gradio as gr


def _choose_folder() -> str:
    """Opens the native folder picker."""
    import tkinter as tk
    from tkinter import filedialog

    root_tk = tk.Tk()
    root_tk.withdraw()
    root_tk.attributes("-topmost", True)
    try:
        return filedialog.askdirectory(title="Choose the folder with documents") or ""
    finally:
        root_tk.destroy()

from biblio import index, meta, pipeline, skill
from biblio.paths import DEFAULT_BIBLIOTHECA, known_bibliothecas, root


def _search_example(bibliotheca: Path) -> str:
    """A real term from what just went in, so the user doesn't have to invent one."""
    for folder in sorted((p for p in bibliotheca.iterdir() if p.is_dir()),
                         key=lambda p: p.stat().st_mtime, reverse=True):
        if terms := meta.read(folder).get("terms"):
            return terms[0]
        return folder.name.replace("-", " ")
    return "your query here"


def _process(files, folder, dest, do_summary, force):
    folder = (folder or "").strip().strip('"')
    targets = list(files or []) + ([folder] if folder else [])
    if not targets:
        yield "Choose files (.pdf, .md, .txt) or provide a folder."
        return

    bibliotheca = root(dest)
    lines, queue = [], []
    for target in targets:
        count = pipeline.ingest(
            target, output=bibliotheca, force=force,
            summary="yes" if do_summary else "no",
            ask=lambda _: True, warn=queue.append,
        )
        lines += queue
        queue.clear()
        lines.append(f"→ {count['ok']} processed, {count['skipped']} unchanged, "
                     f"{count['failed']} failed")
        yield "\n".join(lines)

    index.generate(output=bibliotheca, summary="no")
    skill.install(warn=lines.append)

    lines += [
        "",
        "─" * 60,
        f"Bibliotheca: {bibliotheca.resolve()}",
        "INDEX.md and CLAUDE.md updated. The Claude Code skill is installed,",
        "so it already knows how to search — no setup needed.",
        "",
        "Try it in Claude Code or the terminal:",
        f'    biblio search "{_search_example(bibliotheca)}"',
        "",
        "To restrict a project to this bibliotheca, point the agent to this folder:",
        "the CLAUDE.md in it already restricts search to this corpus.",
    ]
    yield "\n".join(lines)


def launch(output=None, share: bool = False) -> None:
    known = [Path(c).name for c in known_bibliothecas()]
    default = Path(output).name if output else (known[0] if known
                                                else DEFAULT_BIBLIOTHECA.name)

    from biblio.version_check import _installed_version, _remote_version
    v_local, v_remote = _installed_version(), _remote_version()
    version_notice = (f"  **Version {v_remote} available** (installed: {v_local})"
                      f" — run `biblio update` in the terminal to upgrade."
                      if v_remote and v_remote != v_local else "")

    with gr.Blocks(title="biblio") as app:
        gr.Markdown(f"# biblio{version_notice}")
        dest = gr.Dropdown(
            label="Bibliotheca",
            info="One topic per bibliotheca. Type a new name to start another.",
            choices=sorted({*known, default}), value=default,
            allow_custom_value=True,
        )
        file_input = gr.File(label="Files", file_count="multiple",
                             file_types=[".pdf", ".md", ".txt"])
        with gr.Row():
            folder = gr.Textbox(
                label="or an entire folder", scale=4,
                placeholder=r"click Choose folder  —  or paste the path here",
                info="Processes all .pdf, .md and .txt in the folder and subfolders.")
            choose_btn = gr.Button("📁 Choose folder", scale=1)
        choose_btn.click(_choose_folder, None, folder)
        with gr.Row():
            do_summary = gr.Checkbox(
                value=False,
                label="Generate summary and keywords for each document",
                info="Optional. Uses a local model (Ollama). Checking this authorizes "
                     "downloading ~3 GB the first time. Without this, search works the "
                     "same — only the terms line in the index is missing.")
            force = gr.Checkbox(label="Reprocess even without changes")
        btn = gr.Button("Add documents", variant="primary")
        progress = gr.Textbox(label="Progress", lines=18, max_lines=18, autoscroll=True)

        btn.click(_process, [file_input, folder, dest, do_summary, force], progress)
    app.launch(inbrowser=True, share=share)
```

- [ ] **Step 3: Verify both files parse**

Run: `cd /c/Users/Usuario/pedrocosme/dev/fromPDFtoAgenticFriendly && /c/Users/Usuario/.conda/envs/alcoa/python.exe -c "import ast; [ast.parse(open(f'biblio/{f}').read()) for f in ('cli.py','gui.py')]; print('OK')"`

---

### Task 10: Tests — all test files

**Files:**
- Modify: `tests/conftest.py`, `tests/test_triage.py`, `tests/test_normalize.py`, `tests/test_slice.py`, `tests/test_summarize.py`, `tests/test_pipeline.py`, `tests/test_search.py`, `tests/test_idempotencia.py`
- Rename: `tests/test_idempotencia.py` → `tests/test_idempotency.py`

- [ ] **Step 1: Rewrite `tests/conftest.py`**

```python
import pymupdf
import pytest

DENSE_TEXT = ("Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 8)


def _pdf(dest, pages):
    """pages: list of strings; empty string = page without text (simulates scanned)."""
    doc = pymupdf.open()
    for content in pages:
        page = doc.new_page()
        if content:
            page.insert_textbox(pymupdf.Rect(50, 50, 550, 750), content, fontsize=11)
    doc.save(dest)
    doc.close()
    return dest


@pytest.fixture
def native_pdf(tmp_path):
    return _pdf(tmp_path / "native.pdf", [DENSE_TEXT, DENSE_TEXT])


@pytest.fixture
def scanned_pdf(tmp_path):
    return _pdf(tmp_path / "scanned.pdf", ["", ""])


@pytest.fixture
def mixed_pdf(tmp_path):
    return _pdf(tmp_path / "mixed.pdf", [DENSE_TEXT, "", DENSE_TEXT])


@pytest.fixture(autouse=True)
def isolated_registry(tmp_path, monkeypatch):
    """Test never writes to the user's real registry."""
    monkeypatch.setattr("biblio.paths.REGISTRY", tmp_path / "bibliothecas.txt")


@pytest.fixture(autouse=True)
def without_ollama(monkeypatch):
    """Don't call the local model in tests, even if the machine has Ollama running."""
    monkeypatch.setattr("biblio.ollama.available", lambda: False)


CORPUS = {
    "nbr-6118-concreto": [
        ("09-ancoragem.md", "# 9.4 Comprimento de ancoragem\n"
         "O comprimento de ancoragem basico depende da resistencia de aderencia "
         "de calculo entre a barra e o concreto. " * 6),
        ("07-cobrimento.md", "# 7.4 Cobrimento nominal\n"
         "O cobrimento nominal da armadura varia com a classe de agressividade "
         "ambiental. " * 6),
    ],
    "nbr-7480-aco": [
        ("04-ensaios.md", "# 4.3 Ensaio de aderencia\n"
         "Barras nervuradas sao submetidas a ensaio de arrancamento para "
         "verificar a aderencia. " * 6),
    ],
    "manual-inversor": [
        ("02-partida.md", "# 2 Partida suave\n"
         "Configure a rampa de aceleracao do inversor de frequencia para o motor "
         "trifasico. " * 6),
    ],
    "artigo-fadiga": [
        ("03-fadiga.md", "# 3 Fadiga\n"
         "Fatigue life of welded joints under cyclic loading is governed by the "
         "stress range. " * 6),
    ],
}


def _build(root, names):
    """Indexes for real — no fake DB; test 4 validates the chosen model."""
    from biblio import db, embed

    con = db.connect(root)
    for doc in names:
        folder = root / doc
        folder.mkdir()
        for fname, body in CORPUS[doc]:
            (folder / fname).write_text(
                f"---\ndoc: {doc}\nsection: x\n---\n\n{body}\n", encoding="utf-8")
        chunks = embed.doc_chunks(folder)
        db.replace_document(con, doc, chunks,
                            embed.vectorize([c["text"] for c in chunks]))
    con.close()
    return root


@pytest.fixture(scope="session")
def synthetic_bibliotheca(tmp_path_factory):
    """Entire session: the embedding model loads once."""
    return _build(tmp_path_factory.mktemp("lib"),
                  ["nbr-6118-concreto", "nbr-7480-aco", "manual-inversor"])


@pytest.fixture(scope="session")
def secondary_bibliotheca(tmp_path_factory):
    """The second bibliotheca the user creates in another run."""
    return _build(tmp_path_factory.mktemp("lib2"), ["artigo-fadiga"])
```

- [ ] **Step 2: Rewrite `tests/test_triage.py`**

```python
from biblio.triage import route_page, triage


def test_route_page_low_text_goes_to_ocr():
    assert route_page(n_chars=10, has_table=False) == "ocr"


def test_route_page_lots_of_text_and_clean_is_native():
    assert route_page(n_chars=5000, has_table=False) == "native"


def test_route_page_with_table_goes_to_docling():
    assert route_page(n_chars=5000, has_table=True) == "complex"


def test_page_without_text_gets_ocr_even_with_table_detected():
    assert route_page(n_chars=0, has_table=True) == "ocr"


def test_triage_native_document(native_pdf):
    route = triage(native_pdf)
    assert route["native"] == [1, 2]
    assert route["ocr"] == []


def test_triage_scanned_document(scanned_pdf):
    route = triage(scanned_pdf)
    assert route["ocr"] == [1, 2]
    assert route["native"] == []


def test_triage_mixed_document_separates_by_page(mixed_pdf):
    route = triage(mixed_pdf)
    assert route["native"] == [1, 3]
    assert route["ocr"] == [2]
```

- [ ] **Step 3: Rewrite `tests/test_normalize.py`**

```python
from biblio.normalize import normalize


def test_joins_broken_hyphen():
    text = "O comprimento de anco-\nragem depende da aderencia."
    assert "ancoragem" in normalize(text)


def test_does_not_join_legitimate_compound_hyphen():
    text = "Ensaio guarda-\nRoupa nao existe"
    assert "guarda-\nRoupa" in normalize(text) or "guarda-Roupa" not in normalize(text)


def test_removes_repeated_header_across_pages():
    text = "\n".join(f"ABNT NBR 6118:2023\npage content {i}" for i in range(4))
    output = normalize(text)
    assert "ABNT NBR 6118:2023" not in output
    assert output.count("page content") == 4


def test_preserves_repeated_line_that_is_heading():
    text = "# Doc\n" + "\n".join(f"## Requisitos\nbody {i}" for i in range(4))
    assert normalize(text).count("## Requisitos") == 4


def test_removes_bold_slide_footer():
    text = "\n".join(
        f"# Slide {i}\nslide body {i}\n**Conversores - ELE085**\n**{i}**"
        for i in range(1, 6))
    output = normalize(text)
    assert "ELE085" not in output, "repeated bold footer should be removed"
    assert "**1**" not in output and "\n**2**\n" not in output
    assert output.count("slide body") == 5


def test_legitimate_non_repeated_bold_stays():
    text = "# Doc\n**Importante:** leia isto com atencao antes de comecar"
    assert "**Importante:**" in normalize(text)


def test_removes_standalone_page_number():
    text = "useful text\n42\nother useful text\nPagina 43 de 238\nend"
    output = normalize(text)
    assert "\n42\n" not in output
    assert "Pagina 43 de 238" not in output
    assert "useful text" in output and "end" in output


def test_promotes_hierarchy_when_document_starts_at_level_two():
    text = "## Objetivo\nbody\n### Detalhe\nbody"
    output = normalize(text)
    assert output.startswith("# Objetivo")
    assert "## Detalhe" in output


def test_does_not_touch_hierarchy_when_already_at_level_one():
    text = "# Objetivo\nbody\n## Detalhe\nbody"
    assert normalize(text) == text + "\n"


def test_preserves_page_marker():
    text = "<!-- pag 7 -->\n# Titulo\nbody"
    assert "<!-- pag 7 -->" in normalize(text)
```

- [ ] **Step 4: Rewrite `tests/test_slice.py`**

```python
from biblio.slice import FLOOR, CEILING, slice_doc


def test_one_slice_per_heading():
    md = "# Um\n" + "a" * 500 + "\n# Dois\n" + "b" * 500
    slices = slice_doc(md)
    assert [s.section for s in slices] == ["Um", "Dois"]
    assert [s.name for s in slices] == ["01-um.md", "02-dois.md"]


def test_floor_short_section_merges_into_next():
    md = "# Curta\ncorpo minusculo\n# Grande\n" + "b" * (FLOOR + 100)
    slices = slice_doc(md)
    assert len(slices) == 1
    assert "corpo minusculo" in slices[0].text
    assert "# Grande" in slices[0].text


def test_floor_short_section_at_end_merges_into_previous():
    md = "# Grande\n" + "a" * (FLOOR + 100) + "\n# Curta\nfim"
    slices = slice_doc(md)
    assert len(slices) == 1
    assert "fim" in slices[0].text


def test_ceiling_long_section_splits_at_paragraph_with_suffix():
    paragraph = "x" * 1000 + "\n\n"
    md = "# Longa\n" + paragraph * 12
    slices = slice_doc(md)
    assert len(slices) > 1
    assert [s.name for s in slices][:2] == ["01-longa-a.md", "01-longa-b.md"]
    assert all(len(s.text) <= CEILING * 1.1 for s in slices)


def test_parent_points_to_ancestor_heading():
    md = ("# Capitulo\n" + "a" * 500 + "\n## Secao\n" + "b" * 500)
    slices = slice_doc(md)
    assert slices[0].parent is None
    assert slices[1].parent == "01-capitulo.md"


def test_pages_come_from_marker_and_marker_leaves_text():
    md = "<!-- pag 5 -->\n# Titulo\n" + "a" * 500 + "\n<!-- pag 7 -->\n" + "b" * 100
    s = slice_doc(md)[0]
    assert s.page_start == 5
    assert s.page_end == 7
    assert "<!-- pag" not in s.text


def test_text_before_first_heading_is_not_lost():
    md = "preambulo importante\n" + "a" * 500 + "\n# Primeiro\n" + "b" * 500
    slices = slice_doc(md)
    assert "preambulo importante" in slices[0].text


def test_repeated_slide_heading_does_not_split():
    md = ("# Motores\n" + "d" * 500 + "\n"
          "## Circuitos Magneticos\n" + "a" * 300 + "\n"
          "<!-- pag 2 -->\n## circuitos magneticos\n" + "b" * 300 + "\n"
          "<!-- pag 3 -->\n## Circuitos Magneticos.\n" + "c" * 300)
    circ = [s for s in slice_doc(md) if s.section.lower().startswith("circuitos")]
    assert len(circ) == 1
    assert all(x * 50 in circ[0].text for x in "abc")


def test_document_without_heading_becomes_numbered_parts():
    md = ("y" * 1000 + "\n\n") * 200
    names = [s.name for s in slice_doc(md)]
    assert len(names) > 26
    assert names[:2] == ["01-part.md", "02-part.md"]
    assert len(names) == len(set(names))


def test_source_without_pages_does_not_invent_page():
    s = slice_doc("# Titulo\n" + "a" * 500, with_pages=False)[0]
    assert s.page_start is None and s.page_end is None
```

- [ ] **Step 5: Rewrite `tests/test_summarize.py`**

```python
from biblio.summarize import _extract


def test_clean_format():
    r, t = _extract("RESUMO: Um circuito magnetico conduz fluxo.\nTERMOS: relutancia, fmm, fluxo")
    assert r == "Um circuito magnetico conduz fluxo."
    assert t == ["relutancia", "fmm", "fluxo"]


def test_terms_mid_paragraph():
    r, t = _extract("Controle por numero de polos e uma tecnica. TERMOS: polos, Dahlander, estator")
    assert r == "Controle por numero de polos e uma tecnica."
    assert t == ["polos", "Dahlander", "estator"]


def test_wrapped_in_bold_and_list():
    r, t = _extract("**RESUMO:** Fluxo concatenado.\n\n**TERMOS:**\n- fluxo\n- tensao")
    assert r == "Fluxo concatenado."
    assert t == ["fluxo", "tensao"]


def test_no_format_does_not_break():
    r, t = _extract("O documento trata de varias coisas")
    assert r and t == []
```

- [ ] **Step 6: Rewrite `tests/test_pipeline.py`**

```python
from biblio.pipeline import _strip_source_frontmatter


def test_removes_source_frontmatter_and_keeps_body():
    md = "---\ntags: [a/b]\naliases: [x, y]\n---\n\n# Titulo\ncorpo"
    output = _strip_source_frontmatter(md)
    assert not output.startswith("---")
    assert "# Titulo\ncorpo" in output
    assert "*x, y, a/b*" in output, "aliases and tags become searchable line"


def test_no_frontmatter_passes_through():
    md = "# Titulo\ncorpo\n---\nhorizontal divider"
    assert _strip_source_frontmatter(md) == md
```

- [ ] **Step 7: Rewrite `tests/test_search.py`**

```python
from biblio.search import search, format_results, rrf


def test_rrf_sums_both_lists():
    scores = rrf([[10, 20, 30], [30, 40]])
    assert scores[30] > scores[10], "id in both lists must beat the top of one"
    assert scores[10] > scores[20]


def test_rrf_empty_list_does_not_break():
    assert rrf([[], [7]]) == {7: 1 / 61}


def test_portuguese_query_finds_right_file_in_top3(synthetic_bibliotheca):
    results = search("como calcular o comprimento de ancoragem", output=synthetic_bibliotheca, top=3)
    assert any(r["file"] == "09-ancoragem.md" for r in results), results


def test_exact_identifier_found_by_fts(synthetic_bibliotheca):
    results = search("inversor de frequencia", output=synthetic_bibliotheca, top=3)
    assert any(r["doc"] == "manual-inversor" for r in results), results


def test_doc_filter_restricts(synthetic_bibliotheca):
    results = search("aderencia", output=synthetic_bibliotheca, top=5, doc="nbr-7480-aco")
    assert results and all(r["doc"] == "nbr-7480-aco" for r in results)


def test_one_result_per_file(synthetic_bibliotheca):
    results = search("ancoragem aderencia concreto", output=synthetic_bibliotheca, top=5)
    paths = [r["path"] for r in results]
    assert len(paths) == len(set(paths))


def test_output_has_pointer_never_body(synthetic_bibliotheca):
    results = search("comprimento de ancoragem", output=synthetic_bibliotheca, top=3)
    text = format_results(results)
    assert ".md:" in text
    assert "resistencia de aderencia de calculo" not in text, "body leaked into output"
    assert max(len(l) for l in text.splitlines()) < 200, "line too long"


def test_returned_path_is_absolute_and_exists(synthetic_bibliotheca):
    from pathlib import Path
    result = search("comprimento de ancoragem", output=synthetic_bibliotheca, top=1)[0]
    p = Path(result["path"])
    assert p.is_absolute() and p.exists()


def test_context_section_returns_entire_slice(synthetic_bibliotheca):
    from pathlib import Path
    q = "comprimento de ancoragem"
    win = search(q, output=synthetic_bibliotheca, top=1, context="window")[0]
    sec = search(q, output=synthetic_bibliotheca, top=1, context="section")[0]
    n = len(Path(sec["path"]).read_text(encoding="utf-8").splitlines())
    assert (sec["line_start"], sec["line_end"]) == (1, n)
    assert sec["line_end"] - sec["line_start"] >= win["line_end"] - win["line_start"]


def test_search_covers_two_bibliothecas(synthetic_bibliotheca, secondary_bibliotheca):
    query = "fatigue of welded joints under cyclic loading"
    results = search(query, output=[synthetic_bibliotheca, secondary_bibliotheca], top=3)
    assert any(r["doc"] == "artigo-fadiga" for r in results), results


def test_lib_restricts_to_one_bibliotheca(synthetic_bibliotheca, secondary_bibliotheca):
    results = search("fatigue welded joints", output=synthetic_bibliotheca, top=3)
    assert all(r["doc"] != "artigo-fadiga" for r in results)
```

- [ ] **Step 8: Create `tests/test_idempotency.py` (new name) and delete the old file**

```python
import pytest

from biblio.pipeline import ingest


@pytest.fixture
def ingested_bibliotheca(tmp_path, native_pdf):
    output = tmp_path / "lib"
    ingest(native_pdf, output=output)
    return output, native_pdf


def _signature(folder):
    return {p.name: (p.stat().st_mtime_ns, p.read_bytes())
            for p in sorted(folder.rglob("*")) if p.is_file() and p.suffix != ".db"}


def test_second_run_skips_document(ingested_bibliotheca):
    output, pdf = ingested_bibliotheca
    assert ingest(pdf, output=output) == {"ok": 0, "skipped": 1, "failed": 0}


def test_second_run_does_not_rewrite_any_file(ingested_bibliotheca):
    output, pdf = ingested_bibliotheca
    before = _signature(output)
    ingest(pdf, output=output)
    assert _signature(output) == before


def test_force_reprocesses(ingested_bibliotheca):
    output, pdf = ingested_bibliotheca
    assert ingest(pdf, output=output, force=True)["ok"] == 1


def test_reprocessing_does_not_duplicate_chunks(ingested_bibliotheca):
    from biblio import db
    output, pdf = ingested_bibliotheca
    con = db.connect(output)
    before = con.execute("SELECT count(*) FROM chunks").fetchone()[0]
    con.close()
    ingest(pdf, output=output, force=True)
    con = db.connect(output)
    after = con.execute("SELECT count(*) FROM chunks").fetchone()[0]
    con.close()
    assert before == after > 0


def test_markdown_input_is_also_idempotent(tmp_path):
    source = tmp_path / "already-converted.md"
    source.write_text("# Escopo\n" + "texto tecnico. " * 60, encoding="utf-8")
    output = tmp_path / "lib"

    assert ingest(source, output=output)["ok"] == 1
    frontmatter = next((output / "already-converted").glob("[0-9]*.md")).read_text(
        encoding="utf-8")
    assert "pages:" not in frontmatter, "source without pages should not invent pages"
    assert ingest(source, output=output) == {"ok": 0, "skipped": 1, "failed": 0}
```

Then delete the old file:

Run: `rtk git rm tests/test_idempotencia.py`

- [ ] **Step 9: Verify all test files parse**

Run: `cd /c/Users/Usuario/pedrocosme/dev/fromPDFtoAgenticFriendly && /c/Users/Usuario/.conda/envs/alcoa/python.exe -c "import ast; [ast.parse(open(f'tests/{f}').read()) for f in ('conftest.py','test_triage.py','test_normalize.py','test_slice.py','test_summarize.py','test_pipeline.py','test_search.py','test_idempotency.py')]; print('OK')"`

---

### Task 11: `pyproject.toml` + final validation

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Update `pyproject.toml`**

Change version from `"0.1.0"` to `"0.2.0"` and description to English:

```toml
version = "0.2.0"
description = "Document memory layer for agents"
```

- [ ] **Step 2: Run the unit tests that don't need heavy dependencies**

Run: `cd /c/Users/Usuario/pedrocosme/dev/fromPDFtoAgenticFriendly && /c/Users/Usuario/.conda/envs/alcoa/python.exe -m pytest tests/test_normalize.py tests/test_slice.py tests/test_summarize.py tests/test_triage.py -v`

- [ ] **Step 3: Verify all imports resolve**

Run: `cd /c/Users/Usuario/pedrocosme/dev/fromPDFtoAgenticFriendly && /c/Users/Usuario/.conda/envs/alcoa/python.exe -c "from biblio import meta, paths, triage, normalize, ollama, version_check, embed, slice, db, convert, summarize, search, index, skill, pipeline, cli, gui; print('all imports OK')"`

- [ ] **Step 4: Commit (no co-authored-by)**

```bash
rtk git add -A && rtk git commit -m "refactor: rename all Portuguese identifiers and strings to English

Big-bang rename of all Python identifiers, docstrings, comments,
CLI/GUI text, agent instructions, and persisted data keys from
Portuguese to English. Adds automatic migration of _meta.yaml
(translates keys, deletes hash to force reindexation) and SQLite
schema migration (drops old-column tables on connect).

Version bump to 0.2.0 (breaking change in data format)."
```
