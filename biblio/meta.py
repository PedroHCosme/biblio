"""`_meta.yaml`: procedencia, hash e estado. E o que torna reprocessar uma pasta barato."""
import hashlib
from datetime import date
from pathlib import Path

import yaml

NOME = "_meta.yaml"


def hash_arquivo(caminho: Path) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def ler(pasta_doc: Path) -> dict:
    arquivo = pasta_doc / NOME
    return yaml.safe_load(arquivo.read_text(encoding="utf-8")) if arquivo.exists() else {}


def escrever(pasta_doc: Path, dados: dict) -> None:
    pasta_doc.mkdir(parents=True, exist_ok=True)
    (pasta_doc / NOME).write_text(
        yaml.safe_dump(dados, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )


def ja_processado(pasta_doc: Path, digest: str) -> bool:
    """Mesmo hash e sem falha registrada: nao ha o que refazer."""
    anterior = ler(pasta_doc)
    return anterior.get("hash") == digest and not anterior.get("falhou")


def novo(caminho: Path, digest: str, rota: dict[str, list[int]]) -> dict:
    """rota vazia = origem que ja era texto (.md, .txt): nao tem paginas nem OCR."""
    return {
        "origem": str(caminho.resolve()),
        "formato": caminho.suffix.lower().lstrip("."),
        "hash": digest,
        "paginas": sum(len(v) for v in rota.values()) or None,
        "rota": {k: len(v) for k, v in rota.items()},
        "data": date.today().isoformat(),
        "qualidade": "ok",
        "falhou": None,
        "resumo": "pendente",
    }
