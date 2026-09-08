"""Avisa se ha versao mais nova no GitHub. Nunca trava, nunca falha visivelmente."""
import re
import urllib.request

REPO_RAW = "https://raw.githubusercontent.com/PedroHCosme/biblio/main/pyproject.toml"


def _versao_instalada() -> str:
    from importlib.metadata import version
    return version("biblio")


def _versao_remota(timeout: float = 3) -> str | None:
    try:
        with urllib.request.urlopen(REPO_RAW, timeout=timeout) as r:
            texto = r.read().decode()
        m = re.search(r'version\s*=\s*"([^"]+)"', texto)
        return m.group(1) if m else None
    except Exception:
        return None


def checar(avisar=print) -> None:
    """Compara local vs remota. Se diferente, avisa em uma linha. Silencioso se falhar."""
    try:
        local = _versao_instalada()
        remota = _versao_remota()
        if remota and remota != local:
            avisar(f"biblio {local} instalado — versao {remota} disponivel. "
                   "Rode `biblio update` para atualizar.")
    except Exception:
        pass
