---
titulo: biblio — camada de memória documental para agentes
data: 2026-09-07
status: aprovado
autor: Pedro Cosme
---

# biblio — camada de memória documental para agentes

## 1. Problema

Acervo pessoal grande de PDFs técnicos (normas, datasheets, livros, papers), muitos
deles com centenas de páginas, mistura de texto nativo e páginas digitalizadas,
em português e inglês.

Duas dores concretas:

1. **Contexto estoura.** Jogar esses documentos num agente é caro, lento, e o
   agente perde o fio.
2. **Memória entre sessões.** Reenviar o mesmo documento a cada conversa.

Ferramenta pessoal, dois usuários (Pedro e esposa), duas máquinas. Sem ambição
comercial.

## 2. Premissas corrigidas

A ideia original era "converter PDF para Markdown porque MD gasta menos token".
Essa premissa está errada e o registro importa porque ela mudaria o desenho:

- **Markdown não economiza tokens contra texto puro — custa ~2-5% a mais.** Os
  `#`, `|`, `**` são tokens.
- O custo não está no formato, está no **caminho de ingestão**. PDF enviado
  nativamente para uma API vira imagem + texto (~1,5k-3k tokens/página); o texto
  extraído da mesma página custa ~500-800.
- **A economia real vem de ler menos, não de codificar mais barato.** O que
  Markdown compra é estrutura: headings dão pontos de corte confiáveis, o que
  habilita leitura parcial. É isso que corta o custo, não a sintaxe.

Consequência de desenho: o produto **não é um conversor**. Conversão PDF→MD já é
resolvida por Docling, Marker, MinerU, PyMuPDF4LLM, markitdown, Unstructured.
O produto é a **camada de memória** construída em cima dessas ferramentas.

## 3. Decisões

| Decisão | Escolha | Razão |
|---|---|---|
| Consumidor primário | Claude Code (agente com filesystem) | Já tem Read/Grep/Glob; a saída em arquivos serve os outros apps de graça |
| Formato de saída | Pasta de Markdown fatiado + índice + SQLite | Uma pasta de arquivos é comida para Claude Code, Desktop, Cowork e ChatGPT. Um servidor MCP atenderia dois e custaria dez vezes mais |
| Motor vs interface | **CLI é o motor, GUI é casca** | O agente precisa de `biblio search` no shell. Se a GUI virar a única porta, a integração com o agente morre |
| Stack | Python + CLI + Gradio + SQLite | Docling e sentence-transformers são Python; SQLite é um arquivo que viaja com a pasta; Gradio dá drag-drop e progresso de graça |
| Busca | Híbrida: vetorial + FTS5 | Embedding erra feio em identificador exato ("9.4.2", "NBR 6118"). FTS5 já vem no SQLite, custo zero |
| Modelo aberto | Ollama local (`qwen3`) para resumos; RapidOCR/VLM para OCR | Trabalho que só modelo faz |
| Device | Flag `--device auto` | CPU hoje, GPU NVIDIA depois. Isso é uma flag, não uma camada de abstração |

### Fora de escopo (decidido, não esquecido)

- **Knowledge graph.** Extração de entidades gera grafo ruidoso e caro para
  ferramenta pessoal; embedding + índice cobre os casos reais levantados.
- **Servidor MCP.** Os arquivos já servem os quatro apps.
- **Login, contas, multi-tenant, nuvem, Docker.** Dois usuários não justificam.
- **LLM na normalização do texto.** Modelo reescrevendo texto extraído alucina e
  produz documento sutilmente errado — pior que o problema original.
- **Busca e leitura dentro da GUI.** A GUI é painel de ingestão. Busca e leitura
  acontecem no agente ou no editor.
- **Chat/RAG dentro da GUI.**

## 4. Arquitetura

```
PDF → [triar] → [converter] → [normalizar] → [fatiar] → [resumir] → [indexar vetor] → biblioteca/
```

Seis módulos, cada um com entrada e saída em disco. **Cada etapa grava seu
resultado**, então falha na etapa 5 não força reprocessar OCR de 600 páginas.

### 4.1 `triage.py` — decide o caminho barato

Classifica **por página, não por documento.** Uma norma de 600 páginas pode ter
500 nativas e 100 digitalizadas; rodar OCR nas 600 é ~10x mais lento sem ganho.

Heurística: PyMuPDF extrai texto da página; se a densidade de caracteres passa de
um limiar, a página é nativa, senão vai para OCR. Determinístico, ~2s por documento.

Saída: plano de rota `{doc, paginas_nativas: [...], paginas_ocr: [...]}`.

### 4.2 `convert.py` — dois conversores, uma flag

| Situação | Ferramenta |
|---|---|
| Documento nativo, layout simples | `pymupdf4llm` (~50x mais rápido que Docling) |
| Tabelas, colunas, fórmulas, ou páginas OCR | `docling` |

OCR não é um terceiro caminho: é `docling(ocr=True)` com RapidOCR em CPU, e a
mesma chamada com `--device cuda` na máquina com GPU.

### 4.3 `normalize.py` — limpeza determinística

Markdown cru de conversor vem sujo: hífen de quebra de linha, cabeçalho e rodapé
repetidos em toda página, número de página solto, hierarquia de heading quebrada.

Regex e heurística. **Nenhum LLM nesta etapa** (ver Fora de escopo).

### 4.4 `slice.py` — fatia por heading, com piso e teto

- **Piso:** seção de poucas linhas gruda na próxima, para não gerar centenas de
  arquivos inúteis.
- **Teto:** seção grande sem sub-heading quebra por parágrafo, com sufixo `-a`, `-b`.
- Cada arquivo sai com frontmatter YAML.

### 4.5 `summarize.py` — modelo aberto trabalha aqui

Um resumo **por documento**, não por chunk. Gera `_resumo.md` e o bloco do
documento no `INDEX.md` (resumo, árvore de seções, termos-chave). Roda uma vez por
documento; custo zero depois.

Default: Ollama local com `qwen3`. Se Ollama não estiver instalado, a ferramenta
**pergunta** e oferece instalar via `winget install Ollama.Ollama` seguido de
`ollama pull qwen3`. Nunca instala silenciosamente; se o winget falhar ou exigir
elevação, mostra a instrução manual.

### 4.6 `embed.py` — vetores

**A unidade de embedding não é o arquivo.** Um arquivo fatiado pode ter 5.000
tokens; o embedding quer ~500. Chunk é uma janela deslizante *dentro* do arquivo,
guardando ponteiro `arquivo:linha_ini-linha_fim`.

Modelo multilíngue rodando local. Armazenamento em SQLite com `sqlite-vec`, no
mesmo arquivo `.db` que guarda o índice FTS5.

### 4.7 Idempotência

Hash SHA-256 do PDF gravado em `_meta.yaml`. Reprocessar uma pasta pula tudo que
não mudou. **Não é opcional** — sem isso, "processar uma pasta inteira" é
inutilizável na segunda execução.

## 5. Formato de saída

```
biblioteca/
  INDEX.md
  biblio.db                             ← sqlite-vec + FTS5
  nbr-6118-2023-projeto-concreto/
    _meta.yaml                          ← origem, hash, páginas, rota, data, qualidade
    _resumo.md
    09-4-comprimento-de-ancoragem.md
    ...
```

O PDF original **não é copiado**. `_meta.yaml` guarda caminho absoluto e hash;
copiar duplicaria gigabytes.

### 5.1 Frontmatter de cada fatia

```yaml
---
doc: nbr-6118-2023-projeto-concreto
secao: "9.4.2 Comprimento de ancoragem"
paginas: [142, 147]
pai: 09-aderencia-e-ancoragem.md
---
```

Custa ~30 tokens e paga sozinho: quando a busca leva o agente a um arquivo solto,
ele sabe a procedência **sem uma segunda leitura**.

### 5.2 `INDEX.md` — projetado para grep, não para leitura

```markdown
## nbr-6118-2023-projeto-concreto
NBR 6118:2023 — Projeto de estruturas de concreto. 238 pág, texto nativo.
**Termos:** ancoragem, comprimento de aderência, armadura passiva, ELU, fissuração, cobrimento
**Seções:** 01-objetivo · … · 09-aderencia-e-ancoragem · …
`biblioteca/nbr-6118-2023-projeto-concreto/`
```

Restrição explícita: 200 documentos a ~200 tokens cada dá 40k tokens. **O índice
nunca é lido inteiro.** O formato é um bloco por documento, com os termos numa
linha só, para `grep -A4` devolver o bloco fechado.

A linha **Termos** é a rede de segurança: é o que encontra "NBR 6118" quando o
embedding falha.

## 6. Contrato da busca

```
$ biblio search "comprimento de ancoragem" --top 5

nbr-6118-2023.../09-4-comprimento-de-ancoragem.md:1-84   0.89  9.4.2 Comprimento de ancoragem
nbr-6118-2023.../09-3-aderencia.md:12-60                 0.81  9.3 Aderência
nbr-7480-aco.../04-requisitos.md:88-140                  0.74  4.3 Ensaio de aderência
```

**Caminho, linhas, score, heading. Nunca o corpo.** Saída de ~50 tokens. O agente
decide o que abrir e usa `Read` com `offset`/`limit`.

Esta inversão é o núcleo do projeto: **não se empurra contexto para o agente;
ensina-se o agente a se servir.**

Flags: `--top N` · `--doc <nome>` (restringe a um documento) · `--json`.

### 6.1 Busca híbrida

Vetorial e FTS5 rodam em paralelo; resultados são unidos e deduplicados por
arquivo. FTS5 já vem embutido no SQLite, então o custo de dependência é zero.

## 7. Interfaces

### 7.1 CLI — o motor

```
biblio add <pdf|pasta>  [--out biblioteca/] [--device auto] [--force]
biblio search "<query>" [--top 5] [--doc X] [--json]
biblio index                    # regera INDEX.md sem reprocessar
biblio status                   # o que entrou, o que falhou, o que está pendente
biblio gui                      # sobe o Gradio em localhost
biblio shortcut                 # cria o atalho na área de trabalho
```

### 7.2 GUI — a casca

Uma tela em Gradio: arrastar PDFs ou escolher pasta → lista com estado por etapa →
**Processar** → progresso → **Abrir pasta**. Chama a mesma função `add()` que a
CLI chama. **Zero lógica dentro da tela.**

A GUI executa o pipeline de ingestão inteiro sozinha; nenhuma etapa depende de um
agente para orquestrar.

### 7.3 Skill do Claude Code — parte do produto

Uma skill em `.claude/skills/biblioteca/SKILL.md` ensinando o protocolo:

1. Comece por `biblio search "<pergunta reescrita em termos do domínio>"`
2. Leia **só** os arquivos retornados, com `offset`/`limit`
3. Busca vazia → `grep` na linha **Termos** do `INDEX.md`
4. **Nunca** leia o `INDEX.md` inteiro

Sem essa skill o agente dá `Read` na pasta e estoura o contexto — exatamente o
problema que o projeto existe para resolver. Pipeline sem skill é meio produto.

## 8. Instalação

`pip install -e .` seguido de `biblio gui`. Ollama detectado e oferecido na
primeira execução que precisar de resumo. Sem Docker, sem serviço, sem porta fixa.

**Atalho na área de trabalho:** `biblio shortcut` cria o `.lnk` via PowerShell,
sem dependência nova. O alvo do atalho é `pythonw.exe`, não `python.exe` — senão
o atalho abre um console preto junto da GUI.

## 9. Tratamento de erros

| Falha | Comportamento |
|---|---|
| PDF protegido por senha | `_meta.yaml: falhou=senha`, segue para o próximo. **Nunca aborta o lote.** |
| OCR de baixa qualidade | Marca `qualidade=baixa` no meta e **avisa no `INDEX.md`**. O usuário precisa saber que o documento é ruim antes de confiar nele. |
| Ollama indisponível no meio do lote | Pula o resumo, marca `pendente`, continua. `biblio index` regera depois. |
| Interrupção (Ctrl+C) | Estado gravado por etapa; retomar é rodar de novo (coberto pela idempotência). |

Essa coluna é o que separa "processei 200 PDFs" de "processei 12 e crashou".

## 10. Testes

Cinco testes, não uma suíte. Não se testa wrapper de biblioteca de terceiro.

1. **`triage`** — fixtures nativo / escaneado / misto → rota esperada.
2. **`normalize`** — texto com hífen quebrado e header repetido → saída limpa.
   Teste de string puro; o mais barato e o que mais pega regressão.
3. **`slice`** — árvore de heading conhecida → arquivos esperados, **incluindo o
   caso de piso (grudou) e o de teto (quebrou)**.
4. **`search`** — corpus de 5 documentos sintéticos → query conhecida traz o
   arquivo certo no top-3.
5. **Idempotência** — `add` duas vezes na mesma pasta → a segunda execução não
   reescreve nada.

## 11. Riscos e questões em aberto

| # | Questão | Encaminhamento |
|---|---|---|
| 1 | Qual modelo de embedding cabe em CPU? `bge-m3` é forte em português mas pesado; alternativas menores são mais rápidas e piores. | Tarefa de benchmark na fase 0, medindo na máquina real. Decisão baseada em dado, não em preferência. |
| 2 | `sqlite-vec` depende de carregar extensão no SQLite; alguns builds de Python no Windows não habilitam `enable_load_extension`. | Verificar na fase 0. Fallback: busca por força bruta com numpy — para menos de ~500k chunks é instantânea e elimina a dependência. |
| 3 | Limiar de densidade de caracteres da triagem. | Calibrar com PDFs reais do acervo; valor inicial é chute. |
| 4 | Limiar de qualidade de OCR (~70% de palavras reconhecíveis). | Chute inicial; ajustar com dado real. |
| 5 | Tamanho de chunk para embedding (~500 tokens). | Chute inicial; validar com o teste 4. |
| 6 | Onde a biblioteca mora por padrão — pasta fixa global ou uma por projeto? | A decidir na escrita do plano. |
| 7 | Sincronização entre as duas máquinas. | **Fora de escopo.** Cada máquina tem a sua biblioteca; se necessário depois, é problema de pasta sincronizada, não da ferramenta. |
