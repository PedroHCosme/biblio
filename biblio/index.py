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
