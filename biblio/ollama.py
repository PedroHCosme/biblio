"""Deteccao, instalacao consentida e chamada do modelo local."""
import json
import re
import shutil
import subprocess
import urllib.error
import urllib.request

# ponytail: 1.7b. Medido no acervo real (14 aulas + vault): 4b leva ~180s/doc em
# CPU (carga fria de 3GB + prompt-eval) e estoura o timeout nos documentos maiores;
# 1.7b faz o mesmo resumo em ~75s/doc com qualidade suficiente para uma frase + 12
# termos. Suba para 4b se tiver GPU ou se os resumos sairem ruins.
MODELO = "qwen3:1.7b"
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


def gerar(prompt: str, timeout: int = 180, max_tokens: int = 400) -> str:
    # `"think": false` no payload nao desliga o raciocinio do qwen3 nesta versao do
    # Ollama: ele gera ~900 tokens de "Okay, the user asked..." antes da resposta,
    # 10x mais lento em CPU. O marcador `/no_think` no prompt e o que a familia qwen3
    # entende. `<think></think>` residual, se vier, e removido abaixo.
    # num_predict limita a geracao: a tarefa e uma frase + 12 termos (~120 tokens);
    # sem teto o modelo diverte-se por centenas de tokens e o custo em CPU explode.
    corpo = json.dumps({"model": MODELO, "prompt": f"{prompt}\n/no_think",
                        "stream": False, "think": False,
                        "options": {"num_predict": max_tokens}}).encode()
    requisicao = urllib.request.Request(ENDERECO, data=corpo,
                                        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(requisicao, timeout=timeout) as resposta:
        texto = json.load(resposta)["response"]
    return re.sub(r"<think>.*?</think>", "", texto, flags=re.S).strip()
