"""Um resumo por documento (spec 4.5) — nunca por chunk. Roda uma vez, custa zero depois."""
import re
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
    """qwen3:1.7b nem sempre poe RESUMO/TERMOS em linhas separadas: as vezes escreve
    `TERMOS:` no meio do paragrafo, ou envolve em `**`. Parser tolerante a isso.
    """
    texto = resposta.replace("*", "").strip()
    corte = re.search(r"(?i)\btermos?\s*:", texto)
    antes = texto[:corte.start()] if corte else texto
    depois = texto[corte.end():] if corte else ""

    m = re.search(r"(?i)\bresumo\s*:\s*(.+)", antes, re.S)
    resumo = (m.group(1) if m else antes).strip().split("\n")[0].strip()

    depois = depois.split("\n\n")[0]  # para na primeira quebra dupla
    termos = [t.strip(" .;\n\t-") for t in re.split(r"[,\n]", depois)]
    return resumo, [t for t in termos if t][:15]


def resumir(pasta_doc: Path) -> tuple[str, list[str]]:
    """Escreve `_resumo.md` e devolve (resumo, termos). Levanta se o Ollama falhar."""
    resumo, termos = _extrair(ollama.gerar(PROMPT.format(amostra=_amostra(pasta_doc))))
    (pasta_doc / "_resumo.md").write_text(
        f"{resumo}\n\n**Termos:** {', '.join(termos)}\n", encoding="utf-8"
    )
    return resumo, termos
