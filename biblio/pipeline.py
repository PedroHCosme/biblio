"""adicionar(): a unica porta de entrada. CLI e GUI sao cascas sobre ela."""
import re
from pathlib import Path

import yaml

from biblio import db, embed, meta, ollama, summarize
from biblio.convert import converter
from biblio.normalize import normalizar
from biblio.paths import raiz, registrar, slug
from biblio.slice import fatiar
from biblio.triage import triar


EXTENSOES = (".pdf", ".md", ".txt")


def _arquivos(alvo: Path) -> list[Path]:
    if alvo.is_dir():
        return sorted(p for p in alvo.rglob("*") if p.suffix.lower() in EXTENSOES)
    return [alvo]


def _frontmatter(fatia, doc: str) -> str:
    campos = {"doc": doc, "secao": fatia.secao}
    if fatia.pagina_ini is not None:  # origem sem paginas nao inventa o campo
        campos["paginas"] = [fatia.pagina_ini, fatia.pagina_fim]
    campos["pai"] = fatia.pai
    return "---\n" + yaml.safe_dump(campos, allow_unicode=True, sort_keys=False) + "---\n\n"


_FRONTMATTER_FONTE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.S)


def _sem_frontmatter_de_fonte(texto: str) -> str:
    """Vault do Obsidian: todo .md ja vem com frontmatter YAML proprio. Sem tirar,
    ele empilha com o frontmatter do biblio e vira prosa YAML indexada. `aliases` e
    `tags` sao sinonimos deliberados do autor, entao viram uma linha visivel e
    pesquisavel em vez de sumir.
    """
    m = _FRONTMATTER_FONTE.match(texto)
    if not m:
        return texto
    try:
        dados = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        dados = {}
    termos = dados.get("aliases", []) + dados.get("tags", []) if isinstance(dados, dict) else []
    linha = f"*{', '.join(map(str, termos))}*\n\n" if termos else ""
    return linha + texto[m.end():]


def _obter_texto(caminho: Path, device: str, avisar, nome: str) -> tuple[str, dict]:
    """(markdown bruto, rota). Entrada que ja e texto pula triagem e conversao."""
    if caminho.suffix.lower() != ".pdf":
        avisar(f"{nome}: ja e texto, pulando conversao")
        bruto = caminho.read_text(encoding="utf-8", errors="replace")
        return _sem_frontmatter_de_fonte(bruto), {}
    avisar(f"{nome}: triando")
    rota = triar(caminho)
    avisar(f"{nome}: convertendo {sum(len(v) for v in rota.values())} paginas")
    return converter(caminho, rota, device=device), rota


def _processar_um(caminho: Path, biblioteca: Path, device: str, force: bool,
                  avisar, resumir_com_ollama: bool = False) -> str:
    nome = slug(caminho.stem)
    pasta = biblioteca / nome
    digest = meta.hash_arquivo(caminho)

    if not force and meta.ja_processado(pasta, digest):
        avisar(f"{nome}: inalterado, pulando")
        return "pulado"

    # colisao de slug: "Aula 1.pdf" e "aula-1.md" viram a mesma pasta. Sem isto o
    # segundo sobrescreve o primeiro em silencio.
    anterior = meta.ler(pasta).get("origem")
    if anterior and anterior != str(caminho.resolve()):
        avisar(f"{nome}: AVISO — mesmo nome que {Path(anterior).name}, sobrescrevendo")

    try:
        bruto, rota = _obter_texto(caminho, device, avisar, nome)
    except Exception as erro:  # PDF com senha, arquivo corrompido, encoding impossivel
        avisar(f"{nome}: FALHOU ({erro})")
        meta.escrever(pasta, {"origem": str(caminho.resolve()), "hash": digest,
                              "falhou": str(erro)[:120]})
        return "falhou"

    avisar(f"{nome}: fatiando")
    fatias = fatiar(normalizar(bruto), com_paginas=bool(rota))

    for antigo in pasta.glob("[0-9]*.md"):  # reprocessamento nao deixa fatia orfa
        antigo.unlink()
    pasta.mkdir(parents=True, exist_ok=True)
    for fatia in fatias:
        (pasta / fatia.nome).write_text(_frontmatter(fatia, nome) + fatia.texto + "\n",
                                        encoding="utf-8")

    registro = meta.novo(caminho, digest, rota)
    registro["fatias"] = len(fatias)

    avisar(f"{nome}: indexando")
    chunks = embed.chunks_do_documento(pasta)
    con = db.conectar(biblioteca)
    try:
        # sem `with con:` aqui: substituir_documento ja abre a propria transacao
        db.substituir_documento(con, nome, chunks,
                                embed.vetorizar([c["texto"] for c in chunks]))
    finally:
        con.close()  # no Windows, conexao pendurada trava a limpeza do tmp_path
    registro["chunks"] = len(chunks)

    if resumir_com_ollama:
        try:
            resumo, termos = summarize.resumir(pasta)
            registro |= {"resumo": resumo, "termos": termos}
        except Exception as erro:  # Ollama caiu no meio do lote: marca e segue (spec 9)
            avisar(f"{nome}: resumo pendente ({erro})")
    meta.escrever(pasta, registro)
    avisar(f"{nome}: {len(fatias)} fatias")
    return "ok"


def adicionar(alvo: Path | str, saida: Path | str | None = None, device: str = "auto",
              force: bool = False, avisar=print, perguntar=None) -> dict[str, int]:
    """Processa um arquivo (.pdf/.md/.txt) ou uma pasta.

    `avisar` e o unico canal de progresso: a GUI passa o seu.
    """
    biblioteca = raiz(saida)
    biblioteca.mkdir(parents=True, exist_ok=True)
    resumir_com_ollama = ollama.garantir(perguntar) if perguntar else ollama.disponivel()

    contagem = {"ok": 0, "pulado": 0, "falhou": 0}
    for arquivo in _arquivos(Path(alvo)):
        # falha de um arquivo nunca aborta o lote (spec 9)
        try:
            contagem[_processar_um(arquivo, biblioteca, device, force, avisar,
                                   resumir_com_ollama)] += 1
        except Exception as erro:
            avisar(f"{arquivo.name}: FALHOU ({erro})")
            contagem["falhou"] += 1

    if contagem["ok"] or contagem["pulado"]:
        # Registra so depois, e so se sobrou documento: um lote em que tudo falhou
        # poria uma pasta vazia no registro e o nome dela na descricao da skill.
        registrar(biblioteca)
    return contagem
