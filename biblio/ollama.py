"""Deteccao, instalacao consentida e chamada do modelo local."""
import json
import shutil
import subprocess
import urllib.error
import urllib.request

# ponytail: 4b, nao o 8b padrao do `ollama pull qwen3`. A tarefa e uma frase e uma
# lista de termos a partir de 12 mil caracteres; 8b dobra o download e o tempo por
# documento em CPU sem melhorar isso. Suba se os resumos sairem ruins no acervo real.
MODELO = "qwen3:4b"
ENDERECO = "http://localhost:11434/api/generate"

INSTRUCAO_MANUAL = (
    "Instale manualmente:\n"
    "  winget install Ollama.Ollama\n"
    f"  ollama pull {MODELO}\n"
    "Depois rode `biblio index` para gerar os resumos pendentes."
)


def instalado() -> bool:
    return shutil.which("ollama") is not None


def disponivel() -> bool:
    try:
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2)
        return True
    except (urllib.error.URLError, OSError):
        return False


def garantir(perguntar) -> bool:
    """perguntar(texto) -> bool. Devolve True se der para resumir agora."""
    if disponivel():
        return True
    if instalado():
        return False  # instalado mas servico fora do ar; nao cabe a nos subir servico
    if not perguntar(
        "Ollama nao esta instalado. Ele gera os resumos e os termos-chave de cada "
        "documento (o resto do pipeline funciona sem ele). Instalar agora via winget?"
    ):
        return False
    for comando in (["winget", "install", "-e", "--id", "Ollama.Ollama"],
                    ["ollama", "pull", MODELO]):
        if subprocess.run(comando).returncode != 0:
            print(INSTRUCAO_MANUAL)
            return False
    return disponivel()


def gerar(prompt: str, timeout: int = 180) -> str:
    corpo = json.dumps({"model": MODELO, "prompt": prompt, "stream": False,
                        "think": False}).encode()
    requisicao = urllib.request.Request(ENDERECO, data=corpo,
                                        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(requisicao, timeout=timeout) as resposta:
        return json.load(resposta)["response"].strip()
