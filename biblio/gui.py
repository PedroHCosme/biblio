"""Painel de ingestao. Chama pipeline.adicionar() e mostra o que ela avisa.

Sem busca, sem leitura, sem chat (spec 3, fora de escopo).
"""
from pathlib import Path

import gradio as gr

from biblio import index, meta, pipeline, skill
from biblio.paths import BIBLIOTECA_PADRAO, conhecidas_biblioteca, raiz


def _exemplo_de_busca(biblioteca: Path) -> str:
    """Um termo real do que acabou de entrar, para o usuario nao ter que inventar um."""
    for pasta in sorted((p for p in biblioteca.iterdir() if p.is_dir()),
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

    biblioteca = raiz(destino)  # nome vira ~/biblio/<slug>; caminho passa direto
    linhas, fila = [], []
    for alvo in alvos:
        contagem = pipeline.adicionar(
            alvo, saida=biblioteca, force=forcar,
            perguntar=(lambda _: True) if resumir else None,
            avisar=fila.append,
        )
        linhas += fila
        fila.clear()
        linhas.append(f"→ {contagem['ok']} processados, {contagem['pulado']} inalterados, "
                      f"{contagem['falhou']} falharam")
        yield "\n".join(linhas)

    index.gerar(saida=biblioteca, resumir_pendentes=False)
    skill.instalar(avisar=linhas.append)

    # Este bloco e o passo em que a ferramenta passa a valer alguma coisa.
    # Ele fica dentro do produto, nao num README.
    linhas += [
        "",
        "─" * 60,
        f"Biblioteca: {biblioteca.resolve()}",
        "INDEX.md e CLAUDE.md atualizados. A skill do Claude Code esta instalada,",
        "entao ele ja sabe consultar — nao e preciso ensinar nada.",
        "",
        "Experimente, no Claude Code ou no terminal:",
        f'    biblio search "{_exemplo_de_busca(biblioteca)}"',
        "",
        "Para um projeto usar so esta biblioteca, aponte esta pasta para o agente:",
        "o CLAUDE.md dela ja restringe a busca a este acervo.",
    ]
    yield "\n".join(linhas)


def subir(saida=None, share: bool = False) -> None:
    # Nomes, nao caminhos: `raiz()` resolve os dois, e ninguem devia ter que digitar
    # "C:\\Users\\...\\biblio\\direito-constitucional" para guardar um PDF.
    conhecidas = [Path(c).name for c in conhecidas_biblioteca()]
    padrao = Path(saida).name if saida else (conhecidas[0] if conhecidas
                                             else BIBLIOTECA_PADRAO.name)

    with gr.Blocks(title="biblio") as tela:
        gr.Markdown("# biblio")
        destino = gr.Dropdown(
            label="Biblioteca",
            info="Um assunto por biblioteca. Digite um nome novo para comecar outra.",
            choices=sorted({*conhecidas, padrao}), value=padrao,
            allow_custom_value=True,
        )
        arquivos = gr.File(label="Arquivos", file_count="multiple",
                           file_types=[".pdf", ".md", ".txt"])
        # O navegador nao entrega caminho de pasta por upload, e o FileExplorer do
        # Gradio 6 nao deixa selecionar um diretorio inteiro com um clique. Como o
        # servidor roda na propria maquina do usuario, um campo de texto com o
        # caminho da pasta e o que funciona (Task 4.3: campo de texto > seletor que nao abre).
        pasta = gr.Textbox(
            label="ou cole o caminho de uma pasta inteira",
            placeholder=r"C:\Users\voce\Documentos\normas",
            info="Processa todos os .pdf, .md e .txt da pasta e subpastas.")
        with gr.Row():
            resumir = gr.Checkbox(
                value=True,
                label="Gerar resumo e palavras-chave de cada documento",
                info="Usa um modelo local. Na primeira vez baixa ~3 GB; depois "
                     "funciona offline. Sem isto tudo roda, menos os resumos do indice.")
            forcar = gr.Checkbox(label="Reprocessar mesmo sem mudanca")
        botao = gr.Button("Adicionar documentos", variant="primary")
        progresso = gr.Textbox(label="Progresso", lines=18, max_lines=18, autoscroll=True)

        botao.click(_processar, [arquivos, pasta, destino, resumir, forcar], progresso)
    tela.launch(inbrowser=True, share=share)
