"""Onde a bibliotheca mora e como nomes viram caminhos."""
import re
import unicodedata
from pathlib import Path

RAIZ = Path.home() / "biblio"        # onde as bibliothecas moram, uma pasta cada
BIBLIOTHECA_PADRAO = RAIZ / "geral"   # spec risco 6: padrao global, o atalho nao tem cwd util


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
        return BIBLIOTHECA_PADRAO
    texto = str(saida)
    return RAIZ / slug(texto) if Path(texto).parent == Path(".") else Path(texto)


REGISTRO = Path.home() / ".biblio" / "bibliothecas.txt"


def _migrar_registro() -> None:
    """Renomeia bibliotecas.txt -> bibliothecas.txt uma vez, sem perder o que ja
    estava registrado. Deriva o nome antigo de REGISTRO para respeitar monkeypatch.
    """
    antigo = REGISTRO.with_name("bibliotecas.txt")  # antes do nome latino
    if antigo.exists() and not REGISTRO.exists():
        antigo.rename(REGISTRO)


def registrar(bibliotheca: Path) -> None:
    """Move a bibliotheca para o topo da lista. ponytail: um txt, nao um banco."""
    _migrar_registro()
    caminho = str(bibliotheca.resolve())
    conhecidas = [c for c in conhecidas_bibliotheca() if c != caminho]
    REGISTRO.parent.mkdir(parents=True, exist_ok=True)
    REGISTRO.write_text("\n".join([caminho, *conhecidas]) + "\n", encoding="utf-8")


def conhecidas_bibliotheca() -> list[str]:
    """Mais recente primeiro. Some da lista o que foi apagado do disco."""
    _migrar_registro()
    if not REGISTRO.exists():
        return []
    return [linha for linha in REGISTRO.read_text(encoding="utf-8").splitlines()
            if linha.strip() and Path(linha).is_dir()]


def todas(saida=None) -> list[Path]:
    """Bibliothecas a consultar: a(s) pedida(s), ou todas as registradas, ou so a padrao.

    A pedida vem como caminho **ou** como nome de bibliotheca conhecida: o CLAUDE.md
    de uma pasta manda o caminho dela (que muda de maquina para maquina), e um humano
    no terminal manda o nome, que e o que ele ve em `biblio libs`.

    Aceita lista para que teste consulte bibliothecas proprias sem tocar no registro real.
    """
    if isinstance(saida, (list, tuple)):
        return [Path(c) for c in saida]
    if saida:
        pedido = Path(saida)
        if pedido.is_dir():
            return [pedido]
        # nome: devolve o caminho conhecido; nao achou, devolve o pedido mesmo,
        # para quem chamou poder errar dizendo o que foi pedido
        conhecido = [c for c in conhecidas_bibliotheca() if Path(c).name == str(saida)]
        return [Path(conhecido[0])] if conhecido else [pedido]
    return [Path(c) for c in conhecidas_bibliotheca()] or [BIBLIOTHECA_PADRAO]
