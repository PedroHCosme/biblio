"""Detection, consent-based installation, and calling of the local model."""
import json
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

# ponytail: 1.7b measured on real corpus: 4b takes ~180s/doc on CPU, 1.7b ~75s/doc.
MODEL = "qwen3:1.7b"
ENDPOINT = "http://localhost:11434/api/generate"

_INSTALL_OLLAMA = {
    "win32": "winget install -e --id Ollama.Ollama",
    "darwin": "brew install ollama   (or download from https://ollama.com/download)",
}.get(sys.platform, "curl -fsSL https://ollama.com/install.sh | sh")

MANUAL_INSTRUCTIONS = (
    "Install manually:\n"
    f"  {_INSTALL_OLLAMA}\n"
    f"  ollama pull {MODEL}\n"
    "Then run `biblio index` to generate pending summaries."
)


def installed() -> bool:
    return shutil.which("ollama") is not None


def available() -> bool:
    try:
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2)
        return True
    except (urllib.error.URLError, OSError):
        return False


def _has_model() -> bool:
    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2) as r:
            names = [m["name"] for m in json.load(r).get("models", [])]
        return any(n == MODEL or n.startswith(MODEL + "@") for n in names)
    except (urllib.error.URLError, OSError, ValueError, KeyError):
        return False


def wants_summary(mode: str, ask=None, warn=print) -> bool:
    """Mode -> 'can we summarize now?'.

    'no': never. 'auto' (default): if Ollama+model are already ready, confirm
    once per run (default no; `ask` None resolves to no), never downloads.
    'yes': asks and installs what's missing.
    """
    if mode == "no":
        return False
    if mode == "auto" and available() and _has_model():
        if ask is None:
            return False
        return ask("Ollama detected — generate per-document summaries "
                   "(~75s each, CPU)?")
    ok = ensure(ask, allow_install=(mode == "yes"))
    if not ok:
        warn("summaries: Ollama unavailable, continuing without" if mode == "yes"
             else "summaries: Ollama not configured, skipping (--summary enables)")
    return ok


def ensure(ask=None, *, allow_install: bool = False) -> bool:
    """Returns True if summarization is possible now.

    allow_install=False (default): only uses what's already ready, NEVER downloads.
    allow_install=True: if Ollama or the model is missing, asks (`ask(text)
    -> bool`) and installs/downloads. Nothing is installed without that question.
    """
    if available() and _has_model():
        return True
    if not allow_install:
        return False
    if available():
        if ask and ask(
            f"Ollama is running but the model '{MODEL}' (~1.4 GB, generates summaries "
            "and keywords) has not been downloaded. Download now?"
        ):
            try:
                if subprocess.run(["ollama", "pull", MODEL]).returncode == 0:
                    return True
            except OSError:
                pass
            print(f"Run: ollama pull {MODEL}")
        return False
    if installed():
        return False

    if sys.platform != "win32" or not shutil.which("winget"):
        if ask and ask(
            "Ollama is not installed. It generates summaries and keywords "
            "(the rest of the pipeline works without it). See how to install?"
        ):
            print(MANUAL_INSTRUCTIONS)
        return False

    if not ask or not ask(
        "Ollama is not installed. It generates summaries and keywords for each "
        "document (the rest of the pipeline works without it). Install now via winget?"
    ):
        if not ask:
            print(MANUAL_INSTRUCTIONS)
        return False
    for cmd in (["winget", "install", "-e", "--id", "Ollama.Ollama"],
                ["ollama", "pull", MODEL]):
        try:
            ok = subprocess.run(cmd).returncode == 0
        except OSError:
            ok = False
        if not ok:
            print(MANUAL_INSTRUCTIONS)
            return False
    return available()


def generate(prompt: str, timeout: int = 180, max_tokens: int = 400) -> str:
    body = json.dumps({"model": MODEL, "prompt": f"{prompt}\n/no_think",
                        "stream": False, "think": False,
                        "options": {"num_predict": max_tokens, "temperature": 0.2,
                                    "repeat_penalty": 1.2}}).encode()
    req = urllib.request.Request(ENDPOINT, data=body,
                                headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = json.load(resp)["response"]
    except urllib.error.HTTPError as err:
        if err.code == 404:
            raise RuntimeError(f"model '{MODEL}' not installed — run: "
                               f"ollama pull {MODEL}") from None
        raise
    return re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
