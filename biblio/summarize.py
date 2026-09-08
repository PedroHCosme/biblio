"""Um resumo por documento (spec 4.5) — nunca por chunk. Roda uma vez, custa zero depois."""
from pathlib import Path

from biblio import ollama

MAX_AMOSTRA = 6_000  # ponytail: cabeca do documento basta; alem disso so custa prompt-eval em CPU

# Nada de "documento tecnico" aqui: o acervo pode ser norma, contrato, apostila ou
# livro de historia. Adjetivo de dominio no prompt enviesa o resumo do que nao encaixa.
#
# E nada de "responda em portugues": os TERMOS existem para casar com o texto do
# documento no `grep` do INDEX.md. Traduzidos, eles apontam para palavras que nao
# estao la — a rede de seguranca da busca cai justo no documento em outro idioma.
PROMPT = """Voce recebe o inicio de um documento. Responda **no idioma do documento**, \
exatamente neste formato, sem preambulo:

RESUMO: <uma frase dizendo o que o documento e e para que serve>
TERMOS: <8 a 12 termos de busca do assunto, separados por virgula, sem numeracao. \
Use as palavras como aparecem no documento, sem traduzir>

Documento:
{amostra}"""


def _amostra(pasta_doc: Path) -> str:
    partes = []
    for arquivo in sorted(pasta_doc.glob("[0-9]*.md")):
        partes.append(arquivo.read_text(encoding="utf-8"))
        if sum(map(len, partes)) > MAX_AMOSTRA:
            break
    return "".join(partes)[:MAX_AMOSTRA]


def _extrair(resposta: str) -> tuple[str, list[str]]:
    resumo, termos = "", []
    for linha in resposta.splitlines():
        if linha.upper().startswith("RESUMO:"):
            resumo = linha.split(":", 1)[1].strip()
        elif linha.upper().startswith("TERMOS:"):
            termos = [t.strip() for t in linha.split(":", 1)[1].split(",") if t.strip()]
    return resumo, termos


def resumir(pasta_doc: Path) -> tuple[str, list[str]]:
    """Escreve `_resumo.md` e devolve (resumo, termos). Levanta se o Ollama falhar."""
    resumo, termos = _extrair(ollama.gerar(PROMPT.format(amostra=_amostra(pasta_doc))))
    (pasta_doc / "_resumo.md").write_text(
        f"{resumo}\n\n**Termos:** {', '.join(termos)}\n", encoding="utf-8"
    )
    return resumo, termos
