---
titulo: biblio — camada de memória documental para agentes
data: 2026-09-07
status: aprovado
autor: Pedro Cosme
---

# biblio — camada de memória documental para agentes

## 1. Problema

Acervo pessoal grande de documentos técnicos (normas, datasheets, livros, papers),
muitos deles com centenas de páginas, em português e inglês. A maior parte é PDF,
mistura de texto nativo e páginas digitalizadas; parte já foi convertida para
Markdown por outra ferramenta, ou já nasceu em Markdown ou texto puro.

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

A prova: um `.md` já convertido entra na ferramenta e sai valendo mais. Se o
produto fosse conversão, essa entrada seria um no-op.

## 3. Decisões

| Decisão | Escolha | Razão |
|---|---|---|
| Consumidor primário | Claude Code (agente com filesystem) | Já tem Read/Grep/Glob; a saída em arquivos serve os outros apps de graça |
| Formatos de entrada | `.pdf`, `.md`, `.txt` | Um `.md` já convertido tem os mesmos defeitos de um recém-convertido: cabeçalho repetido, hierarquia torta e, sobretudo, **arquivo único gigante**. Ele pula as duas primeiras etapas e ganha as outras quatro. Que a ferramenta agregue valor a um `.md` de entrada é a prova de que o valor nunca esteve na conversão |
| Ensino do agente | Skill instalada automaticamente + `CLAUDE.md` gerado dentro da biblioteca | O usuário não deve precisar ensinar nada. Os dois mecanismos cobrem casos diferentes (§7.3) |
| Várias bibliotecas | Registro de caminhos; a busca cobre todas | O usuário vai criar mais de uma ao longo do tempo (normas, papers). Se a busca só olhasse a padrão, a segunda biblioteca falharia em silêncio |
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
  produz documento sutilmente errado — pior que o problema original. Numa norma
  técnica, um número trocado que *parece* plausível é pior que um trecho
  visivelmente truncado. Isto resolve a ambiguidade de "melhorar um `.md`":
  **melhorar significa deixar utilizável pelo agente** — limpar, fatiar, indexar,
  buscar. Nunca reescrever o conteúdo.
- **Busca e leitura dentro da GUI.** A GUI é painel de ingestão. Busca e leitura
  acontecem no agente ou no editor.
- **Chat/RAG dentro da GUI.**

## 4. Arquitetura

```
PDF ────→ [triar] → [converter] ─┐
                                 ├─→ [normalizar] → [fatiar] → [resumir] → [indexar vetor] → biblioteca/
MD, TXT ─────────────────────────┘
```

Seis módulos, cada um com entrada e saída em disco. **Cada etapa grava seu
resultado**, então falha na etapa 5 não força reprocessar OCR de 600 páginas.

Entrada que já é texto pula as duas primeiras etapas e entra direto na
normalização. É o mesmo pipeline, dois passos mais curto — nenhum caminho
paralelo, nenhuma lógica duplicada.

**Degradação declarada do `.txt`:** sem headings, o fatiamento não tem em que se
apoiar. O arquivo é cortado por tamanho e os nomes de seção saem sem significado.
A busca continua exata (os ponteiros de linha independem de estrutura), mas a
árvore de seções no `INDEX.md` não ajuda. `.txt` entra funcionando e degradado;
`.md` entra em pé de igualdade com PDF.

### 4.1 `triage.py` — decide o caminho barato

Classifica **por página, não por documento.** Uma norma de 600 páginas pode ter
500 nativas e 100 digitalizadas; rodar OCR nas 600 é ~10x mais lento sem ganho.

Heurística: PyMuPDF extrai texto da página; se a densidade de caracteres passa de
um limiar, a página é nativa, senão vai para OCR. Determinístico, ~2s por documento.

Valor inicial do limiar: **200 caracteres extraídos por página**. É um chute a
calibrar (risco #3), mas fica explícito para que a implementação não invente o seu.

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

- **Piso: 400 caracteres.** Seção menor que isso gruda na próxima, para não gerar
  centenas de arquivos inúteis.
- **Teto: 8.000 caracteres.** Seção maior sem sub-heading quebra em limite de
  parágrafo, com sufixo `-a`, `-b`.

Ambos são valores iniciais a calibrar, mas ficam fixados aqui para que a
implementação não escolha os seus.
- Cada arquivo sai com frontmatter YAML.

**Documento sem heading nenhum** (o caso típico do `.txt`): cada pedaço do teto
vira uma fatia própria, numerada, em vez de sufixo alfabético. Sufixo `-a`…`-z`
acaba em 26; um livro em `.txt` passa disso.

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
  CLAUDE.md                             ← ensina o protocolo a quem abrir a pasta
  INDEX.md
  biblio.db                             ← sqlite-vec + FTS5
  nbr-6118-2023-projeto-concreto/
    _meta.yaml                          ← origem, hash, páginas, rota, data, qualidade
    _resumo.md
    09-4-comprimento-de-ancoragem.md
    ...
```

O original **não é copiado**, seja PDF ou Markdown. `_meta.yaml` guarda caminho
absoluto e hash; copiar duplicaria gigabytes e criaria duas verdades.

A pasta é autocontida: o `.db` mora dentro dela, então copiá-la para outra
máquina funciona. O que não viaja é o executável — `biblio search` exige o
`pip install` na máquina de destino.

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

`paginas` **é omitido** quando a origem não tem páginas (`.md`, `.txt`). Campo
ausente é honesto; `paginas: [1, 1]` seria mentira, e mentira em metadado de
procedência é pior que silêncio.

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

### 5.3 `CLAUDE.md` — a biblioteca se explica sozinha

Gerado junto com o `INDEX.md`, ~250 tokens, ensinando o protocolo de consulta:
buscar primeiro, ler só o intervalo devolvido, cair no `grep` dos termos quando a
busca falhar, nunca ler o `INDEX.md` inteiro.

Ele existe porque a skill (§7.3) não cobre tudo: a skill vive na máquina, o
`CLAUDE.md` vive na pasta. Quando a biblioteca é copiada para a outra máquina, ou
aberta pelo Claude Desktop, pelo Cowork ou pelo ChatGPT — que não carregam skills
do Claude Code — é este arquivo que ensina.

O protocolo é o mesmo da skill num ponto só diferente: **o `CLAUDE.md` traz
`--lib` da própria pasta preenchido**. Apontar o Claude para uma pasta passa a
significar "consulte esta biblioteca", não "consulte tudo que existe nesta
máquina" (§6.0). O caminho é gravado na geração; se a pasta for movida ou
copiada, `biblio --out . index` de dentro dela reescreve o arquivo.

Custo em contexto: **zero**, a menos que alguém aponte para a pasta. E quando
aponta, ~250 tokens uma vez, que evitam a leitura de uma biblioteca inteira.

## 6. Contrato da busca

```
$ biblio search "comprimento de ancoragem" --top 3

C:\Users\Usuario\biblio\nbr-6118-2023\09-4-comprimento-de-ancoragem.md:1-84  0.032  9.4.2 Comprimento de ancoragem
C:\Users\Usuario\biblio\nbr-6118-2023\09-3-aderencia.md:12-60                0.028  9.3 Aderência
C:\Users\Usuario\biblio\nbr-7480-aco\04-requisitos.md:88-140                 0.024  4.3 Ensaio de aderência
```

**Caminho, linhas, score, heading. Nunca o corpo.** ~30 tokens por linha; cinco
resultados custam ~150. O agente decide o que abrir e usa `Read` com
`offset`/`limit`.

O caminho é **absoluto**. Com mais de uma biblioteca registrada, caminho relativo
obrigaria o agente a resolver a raiz certa — um passo a mais e um ponto de falha,
para economizar tokens que não são o gargalo.

Esta inversão é o núcleo do projeto: **não se empurra contexto para o agente;
ensina-se o agente a se servir.**

Flags: `--top N` · `--doc <nome>` (restringe a um documento) · `--lib <caminho>`
(restringe a uma biblioteca) · `--json`.

### 6.0 Várias bibliotecas

O usuário vai criar mais de uma ao longo do tempo — normas numa rodada, papers
noutra. Nunca simultaneamente, mas as duas continuam existindo depois.

Cada caminho de biblioteca é registrado em `~/.biblio/bibliotecas.txt`, uma linha
por caminho absoluto. **`biblio search` cobre todas as registradas por padrão**, e
`--lib` restringe.

A alternativa — buscar só na biblioteca padrão — falharia em silêncio: o usuário
ingere papers hoje e amanhã a busca não acha nada, sem dizer por quê. O custo de
varrer todas é uma varredura de matriz por biblioteca, medida na fase 0 em
milissegundos.

A fusão RRF (§6.1) já é a ferramenta certa para unir listas de origens
incomparáveis, então N bibliotecas × 2 buscas são 2N listas no mesmo mecanismo.
Nenhuma matemática nova.

**Uma biblioteca por projeto.** Buscar em todas é o padrão porque o agente
normalmente não sabe onde está a resposta. Mas quando o usuário sabe — o projeto
é de controle digital e o acervo de álgebra linear só faria ruído — há dois
caminhos, e os dois funcionam sem nenhum comando novo:

| Como | O que acontece |
|---|---|
| Copiar a pasta da biblioteca para dentro do projeto | O Claude Code lê o `CLAUDE.md` dela junto com os do projeto e passa a usar `--lib` daquela pasta |
| Apontar o caminho da pasta para o agente | Idem, sem duplicar arquivos |

Apontar é melhor que copiar: uma biblioteca é a mesma em todo projeto e cópias
divergem quando uma delas recebe um documento novo. Copiar existe para o caso de
outra máquina, ou de a pasta viajar junto com um repositório.

A pasta copiada leva o `.biblio.db` dentro (§5), então `--lib` funciona nela sem
registro nenhum — o registro serve para a busca global, não para a restrita. O que
a outra máquina precisa é do `biblio` instalado.

### 6.1 Busca híbrida

Vetorial e FTS5 rodam em paralelo; resultados são unidos e deduplicados por
arquivo. FTS5 já vem embutido no SQLite, então o custo de dependência é zero.

A fusão é por **Reciprocal Rank Fusion**: cada resultado vale `1/(60 + posição)`
na sua própria lista, e os dois valores somam. RRF dispensa normalizar scores de
escalas incomparáveis (cosseno contra BM25) — são poucas linhas e evita o erro
clássico de somar números que não são da mesma grandeza.

## 7. Interfaces

### 7.1 CLI — o motor

```
biblio add <arquivo|pasta>  [--out biblioteca/] [--device auto] [--force]
biblio search "<query>"     [--top 5] [--doc X] [--lib CAMINHO] [--json]
biblio index                    # regera INDEX.md e CLAUDE.md sem reprocessar
biblio status                   # o que entrou, o que falhou, o que está pendente
biblio libs                     # bibliotecas registradas
biblio gui                      # sobe o Gradio em localhost
biblio shortcut                 # cria o atalho na área de trabalho
```

`add` aceita `.pdf`, `.md` e `.txt` — arquivo solto ou pasta varrida recursivamente.

### 7.2 GUI — a casca

Uma tela em Gradio. Chama a mesma função `adicionar()` que a CLI chama.
**Zero lógica dentro da tela.**

```
┌─ biblio ───────────────────────────────────────────┐
│ Biblioteca:  [ C:\Users\Usuario\biblio      ▾ ]    │  ← editável, lista as conhecidas
│                                                    │
│ [ arraste PDF, MD ou TXT aqui ]                    │
│ ou a pasta:  [___________________________]         │
│                                                    │
│ [ ] Instalar Ollama se faltar  [ ] Reprocessar     │
│                                                    │
│              [ Adicionar documentos ]              │
│ ┌────────────────────────────────────────────────┐ │
│ │ progresso, linha a linha                       │ │
│ └────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────┘
```

**O botão é "Adicionar documentos", não "Criar biblioteca".** O uso real é
incremental — documentos entram ao longo de meses, na mesma biblioteca. Um botão
que diz "criar" treina o usuário a fazer uma nova a cada rodada; aí ele tem cinco
bibliotecas e procura em nenhuma. Criar outra continua sendo possível: é digitar
outro caminho no campo do topo, que já vem preenchido com a última usada.

A GUI executa o pipeline de ingestão inteiro sozinha; nenhuma etapa depende de um
agente para orquestrar.

**Ao terminar**, a tela mostra o que conecta a biblioteca ao agente: o caminho da
pasta, a confirmação de que a skill está instalada, e um `biblio search` de
exemplo já preenchido com um termo do que acabou de entrar. Esse é o passo em que
a ferramenta passa a valer alguma coisa, e ele fica dentro do produto — não num
README que ninguém lê.

### 7.3 Ensinar o agente — parte do produto

Sem instrução, o agente dá `Read` na pasta e estoura o contexto: exatamente o
problema que o projeto existe para resolver. **Pipeline sem esta seção é meio
produto.**

O protocolo, em qualquer dos dois veículos, é o mesmo:

1. Comece por `biblio search "<pergunta reescrita em termos do domínio>"`
2. Leia **só** os arquivos retornados, com `offset`/`limit`
3. Busca vazia → `grep` na linha **Termos** do `INDEX.md`
4. **Nunca** leia o `INDEX.md` inteiro

Dois veículos, porque nenhum cobre tudo:

| Veículo | Onde vive | Cobre | Quando entra em contexto |
|---|---|---|---|
| Skill `biblioteca` | `~/.claude/skills/` | Claude Code, sem o usuário apontar nada | Nome e descrição sempre; o corpo quando o agente decide consultar |
| `CLAUDE.md` da biblioteca | dentro da pasta | Pasta copiada para outra máquina; Claude Desktop, Cowork, ChatGPT; **um projeto que quer só esta biblioteca** | Só quando alguém aponta para a pasta |

Os dois veículos diferem num campo: a skill busca em todas as bibliotecas
registradas, o `CLAUDE.md` traz o `--lib` da pasta em que vive. Daí o segundo
veículo não ser redundante com o primeiro nem na máquina do próprio usuário —
é ele que dá escopo (§6.0).

**A skill é instalada automaticamente** — pelo `biblio shortcut` e na primeira
ingestão bem-sucedida, sobrescrevendo a versão anterior. Instalação manual de
skill é um passo que o usuário esquece, e o produto sem ela não funciona.

### 7.4 Orçamento de contexto

A preocupação é legítima: uma ferramenta que economiza tokens não pode custar
tokens. O que o mecanismo de ensino cobra:

| O quê | Quando | Custo |
|---|---|---|
| Descrição da skill | toda sessão do Claude Code | ~20 tokens |
| Corpo da skill | quando o agente decide consultar a biblioteca | ~400 tokens, uma vez |
| `CLAUDE.md` da biblioteca | só se apontarem para a pasta | ~250 tokens, uma vez |
| Saída de `biblio search` | por consulta | ~150 tokens (cinco resultados) |
| Bloco do `INDEX.md` via `grep` | quando a busca falha | ~80 tokens |
| `INDEX.md` inteiro | **nunca** | — |

Uma sessão que consulta a biblioteca três vezes gasta ~900 tokens no total. Uma
única página de PDF enviada nativamente para a API custa mais que isso.

## 8. Instalação

`pip install -e .` seguido de `biblio shortcut` — que cria o atalho **e instala a
skill**. Ollama detectado e oferecido na primeira execução que precisar de resumo.
Sem Docker, sem serviço, sem porta fixa.

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
   caso de piso (grudou), o de teto (quebrou) e o documento sem heading nenhum**.
4. **`search`** — corpus de 5 documentos sintéticos → query conhecida traz o
   arquivo certo no top-3, **e a mesma query cobrindo duas bibliotecas**.
5. **Idempotência** — `add` duas vezes na mesma pasta → a segunda execução não
   reescreve nada.

Os formatos novos de entrada **não ganham um sexto teste**: `.md` e `.txt` entram
como casos dentro dos testes 3 e 5, que é onde a lógica deles de fato mora. O
desvio por extensão em si é um `if`, e `if` não merece suíte.

## 11. Riscos e questões em aberto

| # | Questão | Encaminhamento |
|---|---|---|
| 1 | Qual modelo de embedding cabe em CPU? `bge-m3` é forte em português mas pesado; alternativas menores são mais rápidas e piores. | Tarefa de benchmark na fase 0, medindo na máquina real. Decisão baseada em dado, não em preferência. |
| 2 | `sqlite-vec` depende de carregar extensão no SQLite; alguns builds de Python no Windows não habilitam `enable_load_extension`. | Verificar na fase 0. Fallback: busca por força bruta com numpy — para menos de ~500k chunks é instantânea e elimina a dependência. |
| 3 | Limiar de densidade de caracteres da triagem. | Calibrar com PDFs reais do acervo; valor inicial é chute. |
| 4 | Limiar de qualidade de OCR (~70% de palavras reconhecíveis). | Chute inicial; ajustar com dado real. |
| 5 | Tamanho de chunk para embedding (~500 tokens). | Chute inicial; validar com o teste 4. |
| 6 | ~~Onde a biblioteca mora por padrão?~~ | **Resolvido:** padrão global em `~/biblio/`, sobrescrito por `--out`. O atalho da área de trabalho sobe a GUI sem diretório de trabalho útil, então um padrão global é obrigatório. |
| 7 | Sincronização entre as duas máquinas. | **Fora de escopo.** Cada máquina tem a sua biblioteca; se necessário depois, é problema de pasta sincronizada, não da ferramenta. A pasta é autocontida, então copiá-la funciona — só o `pip install` precisa existir do outro lado. |
| 8 | Quantas bibliotecas até a busca ficar lenta? | A varredura é linear no total de chunks somado. Se incomodar, `--lib` já restringe, e o passo seguinte é indexar por biblioteca — não antes de medir. |
| 9 | `.txt` sem estrutura gera fatias de nome inútil. | Aceito e declarado (§4). A busca continua exata; o que degrada é a navegação pelo `INDEX.md`. Se virar problema, o conserto é inferir heading por heurística — trabalho real, não faça antes de doer. |
