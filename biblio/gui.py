"""Painel de ingestao. Chama pipeline.adicionar() e mostra o que ela avisa.

Sem busca, sem leitura, sem chat (spec 3, fora de escopo).
"""
from pathlib import Path

import gradio as gr


def _escolher_pasta() -> str:
    """Abre o seletor de pastas nativo do sistema. Funciona porque o servidor Gradio
    roda na propria maquina do usuario; o dialogo aparece na area de trabalho dele.
    ponytail: tkinter e stdlib, sem dependencia nova.
    """
    import tkinter as tk
    from tkinter import filedialog

    raiz_tk = tk.Tk()
    raiz_tk.withdraw()
    raiz_tk.attributes("-topmost", True)
    try:
        return filedialog.askdirectory(title="Escolha a pasta com os documentos") or ""
    finally:
        raiz_tk.destroy()

from biblio import index, meta, pipeline, skill
from biblio.paths import BIBLIOTHECA_PADRAO, conhecidas_bibliotheca, raiz


def _exemplo_de_busca(bibliotheca: Path) -> str:
    """Um termo real do que acabou de entrar, para o usuario nao ter que inventar um."""
    for pasta in sorted((p for p in bibliotheca.iterdir() if p.is_dir()),
                        key=lambda p: p.stat().st_mtime, reverse=True):
        if termos := meta.ler(pasta).get("termos"):
            return termos[0]
        return pasta.name.replace("-", " ")
    return "sua pergunta aqui"


def _processar(arquivos, pasta, destino, resumir, forcar):
    # gr.File com type padrao ("filepath") ja entrega str no Gradio >= 4, nao objeto
    pasta = (pasta or "").strip().strip('"')  # "Copiar como caminho" do Windows poe aspas
    alvos = list(arquivos or []) + ([pasta] if pasta else [])
    if not alvos:
        yield "Escolha arquivos (.pdf, .md, .txt) ou informe uma pasta."
        return

    bibliotheca = raiz(destino)  # nome vira ~/biblio/<slug>; caminho passa direto
    linhas, fila = [], []
    for alvo in alvos:
        # checkbox marcada = consentiu com o download (~3 GB, dito no rotulo)
        contagem = pipeline.adicionar(
            alvo, saida=bibliotheca, force=forcar,
            resumo="sim" if resumir else "nao",
            perguntar=lambda _: True, avisar=fila.append,
        )
        linhas += fila
        fila.clear()
        linhas.append(f"→ {contagem['ok']} processados, {contagem['pulado']} inalterados, "
                      f"{contagem['falhou']} falharam")
        yield "\n".join(linhas)

    index.gerar(saida=bibliotheca, resumo="nao")
    skill.instalar(avisar=linhas.append)

    # Este bloco e o passo em que a ferramenta passa a valer alguma coisa.
    # Ele fica dentro do produto, nao num README.
    linhas += [
        "",
        "─" * 60,
        f"Bibliotheca: {bibliotheca.resolve()}",
        "INDEX.md e CLAUDE.md atualizados. A skill do Claude Code esta instalada,",
        "entao ele ja sabe consultar — nao e preciso ensinar nada.",
        "",
        "Experimente, no Claude Code ou no terminal:",
        f'    biblio search "{_exemplo_de_busca(bibliotheca)}"',
        "",
        "Para um projeto usar so esta bibliotheca, aponte esta pasta para o agente:",
        "o CLAUDE.md dela ja restringe a busca a este acervo.",
    ]
    yield "\n".join(linhas)


def subir(saida=None, share: bool = False) -> None:
    # Nomes, nao caminhos: `raiz()` resolve os dois, e ninguem devia ter que digitar
    # "C:\\Users\\...\\biblio\\direito-constitucional" para guardar um PDF.
    conhecidas = [Path(c).name for c in conhecidas_bibliotheca()]
    padrao = Path(saida).name if saida else (conhecidas[0] if conhecidas
                                             else BIBLIOTHECA_PADRAO.name)

    from biblio.version_check import _versao_instalada, _versao_remota
    v_local, v_remota = _versao_instalada(), _versao_remota()
    aviso_versao = (f"  **Versao {v_remota} disponivel** (instalada: {v_local})"
                    f" — rode `biblio update` no terminal para atualizar."
                    if v_remota and v_remota != v_local else "")

    with gr.Blocks(title="biblio") as tela:
        gr.Markdown(f"# biblio{aviso_versao}")
        destino = gr.Dropdown(
            label="Bibliotheca",
            info="Um assunto por bibliotheca. Digite um nome novo para comecar outra.",
            choices=sorted({*conhecidas, padrao}), value=padrao,
            allow_custom_value=True,
        )
        arquivos = gr.File(label="Arquivos", file_count="multiple",
                           file_types=[".pdf", ".md", ".txt"])
        # O navegador nao entrega caminho de pasta por upload e o FileExplorer do
        # Gradio 6 nao seleciona diretorio. O botao abre o seletor nativo do SO
        # (servidor roda na maquina do usuario); o campo fica editavel para ajuste.
        with gr.Row():
            pasta = gr.Textbox(
                label="ou uma pasta inteira", scale=4,
                placeholder=r"clique em Escolher pasta  —  ou cole o caminho aqui",
                info="Processa todos os .pdf, .md e .txt da pasta e subpastas.")
            escolher = gr.Button("📁 Escolher pasta", scale=1)
        escolher.click(_escolher_pasta, None, pasta)
        with gr.Row():
            resumir = gr.Checkbox(
                value=False,
                label="Gerar resumo e palavras-chave de cada documento",
                info="Opcional. Usa um modelo local (Ollama). Marcar autoriza baixar "
                     "~3 GB na primeira vez. Sem isto a busca funciona igual — só falta "
                     "a linha de termos do índice.")
            forcar = gr.Checkbox(label="Reprocessar mesmo sem mudanca")
        botao = gr.Button("Adicionar documentos", variant="primary")
        progresso = gr.Textbox(label="Progresso", lines=18, max_lines=18, autoscroll=True)

        botao.click(_processar, [arquivos, pasta, destino, resumir, forcar], progresso)
    tela.launch(inbrowser=True, share=share)
