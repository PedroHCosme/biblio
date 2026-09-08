# biblio — benchmark no acervo real

Acervo: disciplina **ELE085 – Conversores Eletromecânicos** (UFMG).

- **14 PDFs** — slides de aula, 478 páginas, muita figura e equação
- **Vault Obsidian** — 171 arquivos `.md`: 11 notas de aula + ~145 notas atômicas
  de conceito (`conceitos/`) com wikilinks e frontmatter, + MOCs

Máquina: Windows 11, CPU 8 núcleos, **sem GPU**.

---

## 1. Ingestão

| | valor |
|---|---|
| Documentos processados | **171** (14 PDF + 157 md) · **0 falhas** |
| Páginas PDF | 478, **37% via OCR** (RapidOCR) — slides com pouco texto |
| Tempo de conversão dos PDFs | ~38 min (dominado pelo OCR em CPU) |
| Tempo de ingestão do vault | **108 s** para 171 `.md` |
| Fatias geradas | 423 · Chunks no índice | 444 |
| `biblio.db` | **2,5 MB** |

Reprocessar (`--force`) o acervo inteiro é idempotente: mesma contagem, sem
duplicar chunk.

## 2. Bugs encontrados no material real (todos corrigidos)

Nenhum apareceu nos testes sintéticos; todos vieram do acervo de verdade.

| # | Sintoma | Correção | Commit |
|---|---|---|---|
| 1 | **Frontmatter duplicado** — todo `.md` do vault traz YAML próprio; o pipeline empilhava o dele por cima e o YAML virava prosa indexada | tira o frontmatter da fonte; `aliases`/`tags` viram uma linha pesquisável | `fix: remove frontmatter proprio do .md de entrada` |
| 2 | **Rodapé de slide não removido** — `**Conversores – ELE085**`, `**Departamento…**`, números `**4**` sobreviviam em toda fatia porque `*` era lido como marcador de lista | marcador de lista exige espaço; repetição/nº de página ignora `**negrito**`. Verificado: em aula-1, "ELE085" 18→0 | `fix: normalizacao remove rodape de slide repetido em negrito` |
| 3 | **qwen3 raciocina antes de responder** — `"think": false` no payload não desliga; gerava ~900 tokens de "Okay, the user asked…" por chamada, 10× mais lento | `/no_think` no prompt + remove `<think>` residual | `fix: qwen3 nao raciocina antes do resumo` |
| 4 | **`qwen3:4b` inviável em CPU** — ~180 s/doc, estourava o timeout nos maiores | default → `qwen3:1.7b` + teto de geração (`num_predict=400`) + amostra 6k → **~75 s/aula, ~20 s/nota** | `perf: qwen3:1.7b e teto de geracao` |
| 5 | **Índice mostrava `pendente`** como se fosse o resumo | placeholder tratado como ausente | `fix: INDEX.md nao mostra "pendente" como resumo` |
| 6 | **GUI**: `FileExplorer` do Gradio 6 não seleciona pasta; servidor não subia sem console (pythonw) | campo de texto + botão "📁 Escolher pasta" (seletor nativo via `tkinter`) | `fix: GUI…` / `feat: botao "Escolher pasta"` |

## 3. Busca — 8 consultas no acervo combinado

Verificação: para cada resultado, abrir o arquivo no intervalo de linhas
devolvido e conferir se a seção nomeada está lá.

**Precisão do ponteiro: 24/24.** Todo intervalo devolvido contém de fato a seção.

| Consulta | Tipo | Top-1 devolvido | ✓ |
|---|---|---|---|
| como calcular a velocidade síncrona de um motor | PT semântico | `controle-de-velocidade-do-motor-de-inducao` | ~ (adjacente; `motor-sincrono` no top-3) |
| por que o núcleo do transformador é laminado | PT semântico | `laminacao-do-nucleo` | ✓ |
| what causes eddy current losses in the core | EN→PT | `perdas-por-correntes-parasitas` | ✓ (nem "Foucault" nem "eddy" no texto) |
| slip of an induction motor | EN→PT | `aula-9…/introducao` (define escorregamento) | ✓ |
| ELE085 critério de avaliação | identificador exato | `programa-do-curso-…-ele085` | ✓ (FTS pegou "ELE085") |
| campo magnético girante velocidade síncrona | multi-termo | `velocidade-sincrona-do-campo-girante` | ✓ |
| torque máximo escorregamento crítico | PT técnico | `conjugado-maximo-do-motor-de-inducao` | ✓ ("torque"→"conjugado") |
| equação fasorial do gerador síncrono de rotor cilíndrico | frase longa específica | `maquina-de-polos-salientes` | ✗ (ver abaixo) |

**7 de 8 no alvo. Cross-lingual EN→PT funcionou nas duas consultas.** 8 consultas
em 35 s (carga do modelo incluída).

### A falha (consulta 8) — vale entender

A nota exata `equacao-fasorial-do-gerador-sincrono-de-rotor-cilindrico` **existe** e
casa 6 dos 7 termos, mas fica em **#5**. `maquina-de-polos-salientes` vence — no
espaço de embedding "polos salientes" e "rotor cilíndrico" são vizinhos (ambos são
tipos de rotor de máquina síncrona), e o FTS usa **OR**: uma nota que casa 5 termos
comuns e erra o termo discriminante ("cilíndrico") ainda pontua alto.

**Mitigação** (já no design): `biblio search "…" --doc <nome>` restringe, e a linha
`**Termos:**` do `INDEX.md` (`grep`) é a rede para o termo literal. Melhoria
possível no futuro: bônus de score para match de frase exata no heading.

## 4. biblio vs. o vault Obsidian

Ferramentas diferentes; o que cada uma entrega bem:

| | Vault Obsidian | biblio |
|---|---|---|
| Navegação | grafo, backlinks, wikilinks — feito à mão | busca híbrida, sem curadoria |
| Achar "onde isso é explicado" | precisa saber o nome da nota | pergunta em linguagem natural, PT ou EN |
| Slides de aula (PDF) | não entram | entram, com heading = título do slide |
| Custo em contexto p/ um agente | abrir o vault = centenas de milhares de tokens | 3 buscas ≈ 900 tokens, devolve `arquivo:linhas` |
| Fonte da verdade | as notas atômicas | **aponta de volta** para elas (`file:line`) |

Onde o biblio **ganhou** neste acervo: transformou 478 páginas de slide — que no
vault não existiam — em material pesquisável, com o título do slide como heading
("Campo Magnético", "Circuitos Magnéticos") em vez de "Slide 27". As `aliases` e
`tags` das notas do vault viraram termos de busca extras.

Onde **empatou**: para um conceito que já é uma nota atômica bem nomeada, os dois
levam ao mesmo lugar com esforço parecido.

## 5. Limitação nova encontrada — colisão de slug

`Aula 1 – Circuitos Magnéticos.pdf` e `aula-1-circuitos-magneticos.md` geram **o
mesmo slug** e a segunda ingestão **sobrescreve** a primeira em silêncio (14 notas
de aula do vault foram substituídas pelas versões vindas do PDF). Para este acervo
o resultado é aceitável (o PDF é a fonte melhor), mas a sobrescrita devia avisar.

## 6. Resumos e `INDEX.md`

Com `qwen3:1.7b` os resumos saem bons:

> *aula-1:* "Documento sobre circuitos magnéticos e seus princípios, incluindo o
> campo magnético, efeitos motor, gerador, transformador e relutância."
> *curva-de-magnetização:* "Relação B versus H de um núcleo ferromagnético
> submetido a excitação contínua crescente a partir do estado desmagnetizado."

Backfill dos 171 resumos: ~60–90 min em CPU, em background. Sem isso, o `INDEX.md`
funciona mas sem a linha `**Termos:**` (a rede de segurança para identificador
exato).

## 7. Critérios de aceitação do plano

| # | Critério | Status |
|---|---|---|
| 1 | `add` de pasta com PDF + `.md`, ambos `ok` | ✅ 171/171, 0 falha |
| 2 | Fatia de `.md` sem campo `paginas`; de PDF com | ✅ |
| 3 | 2ª execução → `pulado`, não reescreve nada | ✅ (teste de idempotência) |
| 4 | `search` acha o arquivo certo no top-3, caminho absoluto | ✅ 7/8; ⚠️ 1 caso em #5 |
| 5 | Intervalo devolvido contém a seção do heading | ✅ **24/24** |
| 6 | 2ª biblioteca alcançada pela busca sem flag | ✅ (coberto por `tests/test_search.py`) |
| 7–9 | GUI, atalho, skill se reinstala | ✅ (GUI ajustada p/ Gradio 6) |
| 10–11 | Agente novo usa `biblio search` sozinho / `--lib` ao apontar a pasta | ⏳ manual (sessão nova de Claude Code) |
| 12 | Portabilidade — copiar a pasta, sem conserto | ✅ (nenhum caminho absoluto dentro) |
| 13 | PDF com senha no lote → `falhou`, lote continua | ⏳ sem PDF protegido no acervo |

**Veredito:** o pipeline e a busca entregam o que o projeto prometeu — ponteiro,
nunca corpo; precisão de ponteiro perfeita; cross-lingual real. As arestas
(colisão de slug, 1 consulta específica em #5, resumos lentos em CPU) estão
documentadas e nenhuma bloqueia o uso.
