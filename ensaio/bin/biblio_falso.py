"""`biblio` de mentira: ignora a consulta e imprime ponteiros fixos.

Existe para uma pergunta so, e ela nao e sobre busca: **um agente que ninguem
instruiu prefere chamar isto a ler a pasta?** Se preferir, as 19 tarefas seguintes
valem a pena. Se nao preferir, o mecanismo de ensino precisa mudar antes, e nao
depois de tudo pronto.

Descartavel. Apagar junto com ensaio/ quando a Fase 4 terminar.
"""
import sys
from pathlib import Path

PASTA = Path(__file__).resolve().parent.parent / "acervo-tecnico"
DOC = PASTA / "ni-4471-ancoragem-premoldados"

# Intervalos conferidos a mao contra os arquivos. O primeiro e a secao 5.2, que
# responde a pergunta do ensaio; os outros dois sao ruido plausivel, para que
# escolher o certo seja uma decisao e nao a unica opcao.
PONTEIROS = [
    (DOC / "03-ancoragem.md", 19, 36, 0.041, "5.2 Correcao por posicao de concretagem"),
    (DOC / "02-definicoes.md", 10, 14, 0.029, "3.1 posicao invertida"),
    (DOC / "04-ensaios.md", 15, 20, 0.022, "7.2 Corpo de prova"),
]


def main(argv: list[str]) -> int:
    if not argv or argv[0] != "search":
        print("uso: biblio search \"<consulta>\" [--lib <caminho>]", file=sys.stderr)
        return 2
    for caminho, ini, fim, score, secao in PONTEIROS:
        print(f"{caminho}:{ini}-{fim}  {score:.3f}  {secao}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
