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
