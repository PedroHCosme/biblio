"""Warns if a newer version exists on GitHub. Never blocks, never fails visibly."""
import re
import urllib.request

REPO_RAW = "https://raw.githubusercontent.com/PedroHCosme/bibliotheca/main/pyproject.toml"


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
