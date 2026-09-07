"""Corta o markdown normalizado em fatias por heading, com piso e teto.

Nomes sao `NN-slug-do-heading.md` com NN sequencial. O spec mostra
`09-4-comprimento-de-ancoragem.md` como exemplo cosmetico; ordinal sequencial e
melhor porque ordena certo e funciona em documento sem numeracao de secao.
"""
import re
from dataclasses import dataclass, field

from biblio.paths import slug

PISO = 400    # spec 4.4: secao menor que isso gruda na vizinha
TETO = 8000   # spec 4.4: secao maior que isso quebra em limite de paragrafo

_HEADING = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
_MARCADOR = re.compile(r"^<!-- pag (\d+) -->$")


@dataclass
class Fatia:
    ordem: int
    secao: str
    nivel: int
    texto: str
    pagina_ini: int | None  # None quando a origem nao tem paginas (.md, .txt)
    pagina_fim: int | None
    pai: str | None = None
    sufixo: str = ""

    @property
    def nome(self) -> str:
        return f"{self.ordem:02d}-{slug(self.secao)}{self.sufixo}.md"


@dataclass
class _Bruta:
    secao: str = ""
    nivel: int = 0
    linhas: list[str] = field(default_factory=list)
    paginas: list[int] = field(default_factory=list)

    @property
    def texto(self) -> str:
        return "\n".join(self.linhas).strip()


def _cortar_por_heading(markdown: str) -> list[_Bruta]:
    """Uma secao bruta por heading; o que vem antes do primeiro vira o preambulo."""
    secoes = [_Bruta(secao="", nivel=0)]
    pagina = 1
    for linha in markdown.split("\n"):
        if m := _MARCADOR.match(linha.strip()):
            pagina = int(m.group(1))
            secoes[-1].paginas.append(pagina)
            continue
        if m := _HEADING.match(linha):
            secoes.append(_Bruta(secao=m.group(2), nivel=len(m.group(1)), paginas=[pagina]))
        secoes[-1].linhas.append(linha)
    if not secoes[0].texto:
        secoes.pop(0)
    return secoes


def _aplicar_piso(secoes: list[_Bruta]) -> list[_Bruta]:
    """Secao curta gruda na proxima; se for a ultima, gruda na anterior."""
    juntadas: list[_Bruta] = []
    pendente: _Bruta | None = None
    for secao in secoes:
        if pendente:
            secao = _Bruta(
                secao=pendente.secao or secao.secao,
                nivel=pendente.nivel or secao.nivel,
                linhas=pendente.linhas + secao.linhas,
                paginas=pendente.paginas + secao.paginas,
            )
            pendente = None
        if len(secao.texto) < PISO:
            pendente = secao
            continue
        juntadas.append(secao)
    if pendente:
        if juntadas:
            juntadas[-1].linhas += pendente.linhas
            juntadas[-1].paginas += pendente.paginas
        else:
            juntadas.append(pendente)
    return juntadas


def _quebrar_no_teto(texto: str) -> list[str]:
    if len(texto) <= TETO:
        return [texto]
    pedacos, atual = [], ""
    for paragrafo in texto.split("\n\n"):
        if atual and len(atual) + len(paragrafo) + 2 > TETO:
            pedacos.append(atual)
            atual = paragrafo
        else:
            atual = f"{atual}\n\n{paragrafo}" if atual else paragrafo
    if atual:
        pedacos.append(atual)
    return pedacos


def fatiar(markdown: str, com_paginas: bool = True) -> list[Fatia]:
    """com_paginas=False para origem sem paginas (.md, .txt): o frontmatter omite o campo."""
    brutas = _aplicar_piso(_cortar_por_heading(markdown))
    sem_heading = not any(bruta.nivel for bruta in brutas)

    fatias: list[Fatia] = []
    ancestrais: dict[int, str] = {}  # nivel -> nome do arquivo
    for ordem, bruta in enumerate(brutas, start=1):
        paginas = bruta.paginas or [1]
        pedacos = _quebrar_no_teto(bruta.texto)
        pai = next(
            (nome for nivel, nome in sorted(ancestrais.items(), reverse=True)
             if nivel < bruta.nivel),
            None,
        )
        for i, pedaco in enumerate(pedacos):
            fatias.append(Fatia(
                # Documento sem heading nenhum (tipico de .txt): cada pedaco vira uma
                # fatia numerada. Sufixo alfabetico acabaria em 'z' e um livro passa disso.
                ordem=len(fatias) + 1 if sem_heading else ordem,
                secao="parte" if sem_heading else (bruta.secao or "preambulo"),
                nivel=bruta.nivel,
                texto=pedaco,
                pagina_ini=min(paginas) if com_paginas else None,
                pagina_fim=max(paginas) if com_paginas else None,
                pai=pai,
                # ponytail: sufixo alfabetico so ate 'z'; secao COM heading e 26 pedacos
                # (208 mil caracteres sem sub-heading) nao existe no acervo real.
                sufixo="" if sem_heading or len(pedacos) == 1 else f"-{chr(97 + i)}",
            ))
        if bruta.nivel:
            ancestrais[bruta.nivel] = fatias[-1].nome
            for nivel in [n for n in ancestrais if n > bruta.nivel]:
                del ancestrais[nivel]
    return fatias
