"""Onde a biblioteca mora e como nomes viram caminhos."""
import re
import unicodedata
from pathlib import Path

RAIZ = Path.home() / "biblio"        # onde as bibliotecas moram, uma pasta cada
BIBLIOTECA_PADRAO = RAIZ / "geral"   # spec risco 6: padrao global, o atalho nao tem cwd util


def slug(texto: str, limite: int = 60) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    limpo = re.sub(r"[^a-z0-9]+", "-", sem_acento.lower()).strip("-")
    return limpo[:limite].rstrip("-") or "sem-titulo"


def raiz(saida: Path | str | None = None) -> Path:
    """Aceita nome ou caminho, simetrico ao `--lib` da busca.

    Nome sem barra nenhuma vira pasta debaixo de ~/biblio. Quem digita
    "Direito Constitucional" na GUI nao devia precisar saber o que e caminho
    absoluto — e quem digita um caminho continua mandando nele.
    """
    if not saida:
        return BIBLIOTECA_PADRAO
    texto = str(saida)
    return RAIZ / slug(texto) if Path(texto).parent == Path(".") else Path(texto)
