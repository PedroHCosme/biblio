# biblio

Camada de memoria documental para agentes. Ingere `.pdf`, `.md` e `.txt`, devolve
uma pasta de Markdown fatiado e indexado cuja busca retorna **ponteiros**
(`arquivo:linhas`), nao conteudo — para que o agente leia so o pedaco de que
precisa.

Um `.md` ja convertido por outra ferramenta tambem ganha: ele pula a conversao e
recebe as outras quatro etapas. Se o produto fosse conversao, essa entrada seria
um no-op.

Desenho completo: [`docs/superpowers/specs/2026-09-07-biblio-design.md`](docs/superpowers/specs/2026-09-07-biblio-design.md)

## Instalar

```bash
conda create -n biblio python=3.12 -y
conda activate biblio
pip install -e .
biblio shortcut     # atalho na area de trabalho + instala a skill do Claude Code
```

Ollama e opcional: sem ele tudo funciona, menos os resumos e os termos-chave do
`INDEX.md`. Na primeira ingestao a ferramenta pergunta se quer instalar.

## Usar

```bash
biblio gui                          # painel de ingestao (ou o atalho)
biblio add ~/Documentos/normas      # ou pela linha de comando
biblio search "comprimento de ancoragem"
biblio libs
biblio status
```

## Ligar ao Claude Code

Nada a fazer: a skill se instala em `~/.claude/skills/biblioteca/` no
`biblio shortcut` e a cada ingestao bem-sucedida. Com ela, `biblio search` cobre
todas as bibliotecas conhecidas desta maquina.

Levar uma biblioteca para outro computador e copiar a pasta. Nenhum caminho
absoluto mora dentro dela, entao nao ha o que consertar do outro lado; instale o
`biblio` la e use. A primeira busca com `--lib` na pasta ja a registra.

**Para um projeto usar so uma biblioteca**, aponte o caminho da pasta para o
agente, ou copie a pasta para dentro do projeto. O `CLAUDE.md` dela ensina o
agente a buscar com `--lib`, entao a busca fica restrita aquele acervo. Apontar e
melhor que copiar — copias divergem quando uma recebe documento novo.

**A pasta e portatil.** Nenhum caminho absoluto dentro dela: pode ser movida,
renomeada ou copiada para outro computador sem conserto nenhum. Basta que o
`biblio` esteja instalado la, e usar a pasta uma vez ja a registra naquela maquina.
O que nao viaja junto e o modelo de embedding (~500 MB, baixado na primeira busca).

Custo em contexto de uma sessao que consulta a biblioteca tres vezes: ~900 tokens.
Uma unica pagina de PDF enviada nativamente para a API custa mais que isso.
