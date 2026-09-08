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
