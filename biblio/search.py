"""Busca hibrida. Devolve caminho, linhas, score e heading. Nunca o corpo (spec 6)."""
import re
import unicodedata

from biblio import db, embed
from biblio.paths import conhecidas_bibliotheca, registrar, todas

K_RRF = 60      # constante classica do Reciprocal Rank Fusion
MULTIPLO = 4    # cada lista traz top*4 antes da fusao, para a fusao ter o que fundir
BONUS_HEADING = 0.03  # medido: r@1 56%->80% num eval de 25 consultas no acervo real

# palavras de pergunta que nao discriminam nada — nao contam no casamento com o heading
_VAZIAS = set("o a e de do da os as em para por com como ou no na um uma dos das que "
              "qual quais entre sobre the of a an is are what how why".split())


def _tokens(texto: str) -> set[str]:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return {t for t in re.findall(r"[a-z0-9]{3,}", sem_acento.lower()) if t not in _VAZIAS}


def rrf(listas: list[list]) -> dict:
    """1/(K + posicao) por lista, somado. Dispensa normalizar cosseno contra BM25.

    A chave e opaca: com varias bibliothecas ela e (bibliotheca, id), porque id de
    chunk so e unico dentro de um banco.
    """
    pontos: dict = {}
    for lista in listas:
        for posicao, chave in enumerate(lista, start=1):
            pontos[chave] = pontos.get(chave, 0.0) + 1 / (K_RRF + posicao)
    return pontos


def buscar(consulta: str, saida=None, top: int = 5, doc: str | None = None) -> list[dict]:
    """Cobre todas as bibliothecas registradas, salvo `saida` (caminho ou lista)."""
    candidatos = top * MULTIPLO
    vetor = embed.vetorizar_consulta(consulta)

    listas: list[list] = []
    linhas: dict = {}
    for bibliotheca in todas(saida):
        if not (bibliotheca / db.ARQUIVO).exists():  # nao cria banco em pasta alheia
            if saida is None:
                continue
            # Pasta pedida de proposito. Silencio aqui vira "zero resultados" sem
            # causa, e o agente conclui que o acervo nao sabe a resposta.
            raise SystemExit(
                f'{bibliotheca}: nao e uma bibliotheca biblio (falta {db.ARQUIVO}).\n'
                f'Passe o caminho da pasta, ou um nome de `biblio libs`.')
        if saida is not None and str(bibliotheca.resolve()) not in conhecidas_bibliotheca():
            # Usar uma pasta uma vez ja a torna conhecida desta maquina: uma copia
            # vinda de outro computador entra na busca global sem comando nenhum.
            registrar(bibliotheca)
        con = db.conectar(bibliotheca)
        try:
            ranques = [db.buscar_vetorial(con, vetor, candidatos, doc),
                       db.buscar_fts(con, consulta, candidatos, doc)]
            for identificador, linha in db.detalhes(
                    con, list({i for r in ranques for i in r})).items():
                linhas[(bibliotheca, identificador)] = linha
            listas += [[(bibliotheca, i) for i in r] for r in ranques]
        finally:
            con.close()

    # Bonus de heading: uma fatia cujo titulo casa com a pergunta sobe. Sem isto, a
    # aula que cobre 40 topicos ganha da nota atomica que responde exatamente um.
    q_tokens = _tokens(consulta)
    pontuados = rrf(listas)
    if q_tokens:
        for chave, linha in linhas.items():
            casa = q_tokens & _tokens(linha["secao"] or "")
            if casa:
                pontuados[chave] = pontuados.get(chave, 0.0) + \
                    BONUS_HEADING * len(casa) / len(q_tokens)

    achados: list[dict] = []
    vistos: set[str] = set()
    for (bibliotheca, identificador), ponto in sorted(pontuados.items(),
                                                     key=lambda p: -p[1]):
        linha = linhas.get((bibliotheca, identificador))
        if linha is None:
            continue
        # caminho absoluto: com varias bibliothecas, caminho relativo obrigaria o
        # agente a adivinhar a raiz certa (spec 6)
        caminho = str((bibliotheca / linha["doc"] / linha["arquivo"]).resolve())
        if caminho in vistos:  # spec 6.1: deduplicado por arquivo, fica o melhor
            continue
        vistos.add(caminho)
        achados.append({
            "caminho": caminho, "doc": linha["doc"], "arquivo": linha["arquivo"],
            "secao": linha["secao"], "linha_ini": linha["linha_ini"],
            "linha_fim": linha["linha_fim"], "score": round(ponto, 4),
        })
        if len(achados) == top:
            break
    return achados


def formatar(achados: list[dict]) -> str:
    if not achados:
        return "nada encontrado"
    return "\n".join(
        f"{a['caminho']}:{a['linha_ini']}-{a['linha_fim']}"
        f"  {a['score']:.3f}  {a['secao']}"
        for a in achados
    )
