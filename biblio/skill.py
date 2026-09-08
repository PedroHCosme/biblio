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
