"""Gera INDEX.md e CLAUDE.md a partir da biblioteca em disco. Nunca reprocessa original."""
from pathlib import Path

from biblio import meta, skill, summarize
from biblio.paths import raiz, registrar

CABECALHO = """# Biblioteca

Indice para `grep`, nao para leitura. Um bloco por documento; a linha **Termos** e
o caminho de recuperacao quando a busca semantica falha.

Use `biblio search "<consulta>"` primeiro. Nunca leia este arquivo inteiro.

Nao consegue executar `biblio search`? Entao este indice e a porta de entrada:
ache o bloco do documento pela linha **Termos** e leia so as secoes que o bloco
nomeia. Medido na Tarefa 0.0: um agente sem instrucao previa da `cat` na pasta
inteira, e e a unica coisa aqui que nao tem conserto depois.

"""


def _procedencia(dados: dict) -> str:
    """Origem que ja era texto nao tem pagina nem OCR: nao invente nenhum dos dois."""
    if not (paginas := dados.get("paginas")):
        return dados.get("formato", "texto")
    rota = dados.get("rota", {})
    natureza = f"{rota['ocr']} pag. de OCR" if rota.get("ocr") else "texto nativo"
    return f"{paginas} pag, {natureza}"


def _bloco(pasta: Path, dados: dict) -> str:
    resumo = dados.get("resumo")
    if not resumo or resumo == "pendente":  # "pendente" e o placeholder de meta.novo
        resumo = "sem resumo"
    linhas = [
        f"## {pasta.name}",
        f"{resumo} {_procedencia(dados)}.",
    ]
    if dados.get("falhou"):
        linhas.append(f"**FALHOU:** {dados['falhou']}")
    if dados.get("qualidade") == "baixa":
        linhas.append("**AVISO:** OCR de baixa qualidade, confira contra o original.")
    if termos := dados.get("termos"):
        linhas.append(f"**Termos:** {', '.join(termos)}")
    secoes = sorted(p.stem for p in pasta.glob("[0-9]*.md"))
    if secoes:
        # ponytail: uma aula com 40 fatias despejava 40 slugs (20% do INDEX.md).
        # 8 dao a ideia; quem quer a lista exata roda `biblio search --doc <nome>`.
        mostra = secoes[:8] + ([f"… (+{len(secoes) - 8})"] if len(secoes) > 8 else [])
        linhas.append(f"**Secoes:** {' · '.join(mostra)}")
    linhas.append(f"`{pasta.name}/`")
    return "\n".join(linhas) + "\n"


def gerar(saida=None, resumir_pendentes: bool = True, avisar=print) -> Path:
    biblioteca = raiz(saida)
    biblioteca.mkdir(parents=True, exist_ok=True)  # `biblio index` antes do primeiro add
    blocos = []
    for pasta in sorted(p for p in biblioteca.iterdir() if p.is_dir()):
        dados = meta.ler(pasta)
        if not dados:
            continue
        if resumir_pendentes and dados.get("resumo") == "pendente":
            try:
                resumo, termos = summarize.resumir(pasta)
                dados |= {"resumo": resumo, "termos": termos}
                meta.escrever(pasta, dados)
                avisar(f"{pasta.name}: resumo gerado")
            except Exception as erro:
                avisar(f"{pasta.name}: resumo segue pendente ({erro})")
        blocos.append(_bloco(pasta, dados))

    if blocos:
        # Pasta com documentos e biblioteca desta maquina, mesmo que tenha vindo de
        # outra: `biblio --out <pasta> index` e como uma copia entra na busca global.
        # Pasta vazia nao entra: sujaria a descricao da skill com um nome sem acervo.
        registrar(biblioteca)

    (biblioteca / "CLAUDE.md").write_text(skill.texto_claude_md(), encoding="utf-8")
    destino = biblioteca / "INDEX.md"
    destino.write_text(CABECALHO + "\n".join(blocos), encoding="utf-8")
    return destino
