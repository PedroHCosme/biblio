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
