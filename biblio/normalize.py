"""Limpeza deterministica do markdown cru. Nenhum LLM aqui (spec 3, fora de escopo)."""
import re
from collections import Counter

LIMIAR_REPETICAO = 3       # linha curta repetida N+ vezes e cabecalho/rodape
MAX_CARACTERES_CABECALHO = 80

_HIFEN_QUEBRADO = re.compile(r"(\w)-\n([a-zà-ÿ])")
_SO_NUMERO = re.compile(r"^\s*\d{1,4}\s*$")
_PAGINA_DE = re.compile(r"^\s*(p[áa]g(ina)?\.?\s*)?\d{1,4}\s*(de|/|of)\s*\d{1,4}\s*$", re.I)
_HEADING = re.compile(r"^(#{1,6})\s+\S")
_MARCADOR = re.compile(r"^<!-- pag \d+ -->$")


def _e_estrutura(linha: str) -> bool:
    """Heading, lista, tabela ou marcador: nunca some, por mais que se repita."""
    despido = linha.strip()
    return bool(
        _HEADING.match(despido)
        or _MARCADOR.match(despido)
        or despido.startswith(("|", ">", "-", "*", "```"))
    )


def _remover_repetidos(linhas: list[str]) -> list[str]:
    candidatas = Counter(
        linha.strip() for linha in linhas
        if linha.strip() and len(linha.strip()) <= MAX_CARACTERES_CABECALHO
        and not _e_estrutura(linha)
    )
    lixo = {texto for texto, n in candidatas.items() if n >= LIMIAR_REPETICAO}
    return [linha for linha in linhas if linha.strip() not in lixo]


def _remover_numeros_de_pagina(linhas: list[str]) -> list[str]:
    return [
        linha for linha in linhas
        if not (_SO_NUMERO.match(linha) or _PAGINA_DE.match(linha))
    ]


def _promover_hierarquia(linhas: list[str]) -> list[str]:
    niveis = [len(m.group(1)) for linha in linhas if (m := _HEADING.match(linha.strip()))]
    if not niveis or min(niveis) == 1:
        return linhas
    delta = min(niveis) - 1
    return [
        linha[delta:] if _HEADING.match(linha.strip()) and linha.startswith("#") else linha
        for linha in linhas
    ]


def normalizar(markdown: str) -> str:
    texto = _HIFEN_QUEBRADO.sub(r"\1\2", markdown)
    linhas = texto.split("\n")
    linhas = _remover_repetidos(linhas)
    linhas = _remover_numeros_de_pagina(linhas)
    linhas = _promover_hierarquia(linhas)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(linhas)).strip() + "\n"
