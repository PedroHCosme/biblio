"""Deteccao, instalacao consentida e chamada do modelo local."""
import json
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

# ponytail: 1.7b. Medido no acervo real (14 aulas + vault): 4b leva ~180s/doc em
# CPU (carga fria de 3GB + prompt-eval) e estoura o timeout nos documentos maiores;
# 1.7b faz o mesmo resumo em ~75s/doc com qualidade suficiente para uma frase + 12
# termos. Suba para 4b se tiver GPU ou se os resumos sairem ruins.
MODELO = "qwen3:1.7b"
ENDERECO = "http://localhost:11434/api/generate"

_INSTALA_OLLAMA = {
    "win32": "winget install -e --id Ollama.Ollama",
    "darwin": "brew install ollama   (ou baixe em https://ollama.com/download)",
}.get(sys.platform, "curl -fsSL https://ollama.com/install.sh | sh")

INSTRUCAO_MANUAL = (
    "Instale manualmente:\n"
    f"  {_INSTALA_OLLAMA}\n"
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


def _tem_modelo() -> bool:
    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2) as r:
            nomes = [m["name"] for m in json.load(r).get("models", [])]
        return any(n == MODELO or n.startswith(MODELO + "@") for n in nomes)
    except (urllib.error.URLError, OSError, ValueError, KeyError):
        return False


def quer_resumo(modo: str, perguntar=None, avisar=print) -> bool:
    """Modo -> 'da para resumir agora?'.

    'nao'  : nunca. 'auto' (padrao): so se o Ollama+modelo ja estiverem prontos,
    sem baixar nada. 'sim': pergunta e instala o que faltar.
    """
    if modo == "nao":
        return False
    ok = garantir(perguntar, permitir_instalar=(modo == "sim"))
    if not ok:
        avisar("resumos: Ollama indisponivel, seguindo sem" if modo == "sim"
               else "resumos: Ollama nao configurado, pulando (--summary habilita)")
    return ok


def garantir(perguntar=None, *, permitir_instalar: bool = False) -> bool:
    """Devolve True se da para resumir agora.

    permitir_instalar=False (padrao): so usa o que ja esta pronto, NUNCA baixa nada.
    permitir_instalar=True: se faltar Ollama ou o modelo, pergunta (`perguntar(texto)
    -> bool`) e instala/baixa. Nada e instalado sem essa pergunta.
    """
    if disponivel() and _tem_modelo():
        return True
    if not permitir_instalar:
        return False
    if disponivel():
        # Ollama instalado por fora, mas o modelo dos resumos nunca foi baixado.
        if perguntar and perguntar(
            f"Ollama esta rodando mas o modelo '{MODELO}' (~1,4 GB, gera os resumos "
            "e termos-chave) nao foi baixado. Baixar agora?"
        ):
            try:
                if subprocess.run(["ollama", "pull", MODELO]).returncode == 0:
                    return True
            except OSError:
                pass
            print(f"Rode: ollama pull {MODELO}")
        return False
    if instalado():
        return False  # instalado mas servico fora do ar; nao cabe a nos subir servico

    # Auto-instalacao so via winget (Windows). Nos outros sistemas, instrucao manual:
    # cada gerenciador de pacote e diferente e nao cabe adivinhar.
    if sys.platform != "win32" or not shutil.which("winget"):
        if perguntar and perguntar(
            "Ollama nao esta instalado. Ele gera os resumos e os termos-chave "
            "(o resto do pipeline funciona sem ele). Ver como instalar?"
        ):
            print(INSTRUCAO_MANUAL)
        return False

    if not perguntar or not perguntar(
        "Ollama nao esta instalado. Ele gera os resumos e os termos-chave de cada "
        "documento (o resto do pipeline funciona sem ele). Instalar agora via winget?"
    ):
        if not perguntar:
            print(INSTRUCAO_MANUAL)
        return False
    for comando in (["winget", "install", "-e", "--id", "Ollama.Ollama"],
                    ["ollama", "pull", MODELO]):
        try:
            ok = subprocess.run(comando).returncode == 0
        except OSError:
            ok = False
        if not ok:
            print(INSTRUCAO_MANUAL)
            return False
    return disponivel()


def gerar(prompt: str, timeout: int = 180, max_tokens: int = 400) -> str:
    # `"think": false` no payload nao desliga o raciocinio do qwen3 nesta versao do
    # Ollama: ele gera ~900 tokens de "Okay, the user asked..." antes da resposta,
    # 10x mais lento em CPU. O marcador `/no_think` no prompt e o que a familia qwen3
    # entende. `<think></think>` residual, se vier, e removido abaixo.
    # num_predict limita a geracao: a tarefa e uma frase + 12 termos (~120 tokens);
    # sem teto o modelo diverte-se por centenas de tokens e o custo em CPU explode.
    # temperature baixa + repeat_penalty: 1.7b as vezes ecoa a linha de aliases ou
    # entra em loop ("cmake-gmock, cmake-gtest, ..."); isto estabiliza a saida.
    corpo = json.dumps({"model": MODELO, "prompt": f"{prompt}\n/no_think",
                        "stream": False, "think": False,
                        "options": {"num_predict": max_tokens, "temperature": 0.2,
                                    "repeat_penalty": 1.2}}).encode()
    requisicao = urllib.request.Request(ENDERECO, data=corpo,
                                        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(requisicao, timeout=timeout) as resposta:
            texto = json.load(resposta)["response"]
    except urllib.error.HTTPError as erro:
        if erro.code == 404:  # Ollama no ar, modelo nao baixado
            raise RuntimeError(f"modelo '{MODELO}' nao instalado — rode: "
                               f"ollama pull {MODELO}") from None
        raise
    return re.sub(r"<think>.*?</think>", "", texto, flags=re.S).strip()
