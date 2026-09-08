"""argparse e nada mais. Toda a logica mora nos modulos; aqui so tem parsing."""
import argparse
import json
import sys
from pathlib import Path

from biblio import index, meta, pipeline, search, skill
from biblio.paths import conhecidas_bibliotheca, raiz


def _perguntar(texto: str) -> bool:
    return input(f"{texto} [s/N] ").strip().lower() in ("s", "sim", "y", "yes")


def _status(args) -> int:
    bibliotheca = raiz(args.out)
    if not bibliotheca.exists():
        print(f"bibliotheca vazia: {bibliotheca}")
        return 0
    for pasta in sorted(p for p in bibliotheca.iterdir() if p.is_dir()):
        dados = meta.ler(pasta)
        if not dados:
            continue
        estado = dados.get("falhou") or (
            "resumo pendente" if dados.get("resumo") == "pendente" else "ok")
        origem = f"{dados['paginas']} pag" if dados.get("paginas") else dados.get(
            "formato", "?")
        print(f"{pasta.name:<45} {origem:>8}  "
              f"{dados.get('fatias','?'):>3} fatias  {estado}")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="biblio",
                                description="Camada de memoria documental para agentes")
    p.add_argument("--out", help="pasta da bibliotheca (padrao: ~/biblio)")
    sub = p.add_subparsers(dest="comando", required=True)

    a = sub.add_parser("add", help="ingere .pdf, .md ou .txt — arquivo ou pasta")
    a.add_argument("alvo")
    a.add_argument("--device", default="auto", help="auto | cpu | cuda")
    a.add_argument("--force", action="store_true", help="reprocessa mesmo sem mudanca")
    a.add_argument("--summary", dest="resumo", action="store_const", const="sim",
                   default="auto", help="gera resumo/termos por documento; baixa "
                   "Ollama+qwen se preciso (perguntando antes)")
    a.add_argument("--no-summary", dest="resumo", action="store_const", const="nao",
                   help="nunca gera resumo/termos, mesmo com Ollama disponivel")

    b = sub.add_parser("search", help="busca e devolve ponteiros")
    b.add_argument("consulta")
    b.add_argument("--top", type=int, default=5)
    b.add_argument("--doc", help="restringe a um documento")
    b.add_argument("--lib", help="restringe a uma bibliotheca: caminho ou nome "
                                 "(padrao: todas as conhecidas)")
    b.add_argument("--context", choices=("secao", "janela"), default="secao",
                   help="secao: a fatia inteira (padrao); janela: so o trecho que casou")
    b.add_argument("--json", action="store_true")

    i = sub.add_parser("index", help="regera INDEX.md e CLAUDE.md sem reprocessar")
    i.add_argument("--summary", dest="resumo", action="store_const", const="sim",
                   default="auto", help="preenche resumos pendentes; instala o "
                   "Ollama+qwen se preciso (perguntando antes)")
    i.add_argument("--no-summary", dest="resumo", action="store_const", const="nao",
                   help="so regera INDEX.md/CLAUDE.md, sem tocar em resumo")
    sub.add_parser("status", help="o que entrou, o que falhou, o que esta pendente")
    sub.add_parser("libs", help="bibliothecas registradas")
    sub.add_parser("skill", help="instala a skill do Claude Code (sem criar atalho)")
    sub.add_parser("gui", help="sobe a interface em localhost")
    sub.add_parser("shortcut", help="cria o atalho na area de trabalho")

    args = p.parse_args(argv)

    if args.comando == "add":
        contagem = pipeline.adicionar(Path(args.alvo), saida=args.out, device=args.device,
                                      force=args.force, perguntar=_perguntar,
                                      resumo=args.resumo)
        index.gerar(saida=args.out, resumo="nao")
        if contagem["ok"]:
            skill.instalar()  # o produto sem ela nao funciona; nao dependa de o usuario lembrar
        print(f"\n{contagem['ok']} processados, {contagem['pulado']} inalterados, "
              f"{contagem['falhou']} falharam")
        return 1 if contagem["falhou"] else 0

    if args.comando == "search":
        achados = search.buscar(args.consulta, saida=args.lib or args.out,
                                top=args.top, doc=args.doc, contexto=args.context)
        print(json.dumps(achados, ensure_ascii=False) if args.json
              else search.formatar(achados))
        return 0

    if args.comando == "index":
        destino = index.gerar(saida=args.out, resumo=args.resumo, perguntar=_perguntar)
        skill.instalar()  # bibliotheca vinda de outra maquina entra na descricao aqui
        print(destino)
        return 0

    if args.comando == "status":
        return _status(args)

    if args.comando == "libs":
        for caminho in conhecidas_bibliotheca() or ["(nenhuma; rode `biblio add`)"]:
            print(caminho)
        return 0

    if args.comando == "skill":
        print(skill.instalar())
        return 0

    if args.comando == "gui":
        from biblio.gui import subir
        subir(saida=args.out)
        return 0

    if args.comando == "shortcut":
        from biblio.shortcut import criar
        if lnk := criar():
            print(lnk)
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
