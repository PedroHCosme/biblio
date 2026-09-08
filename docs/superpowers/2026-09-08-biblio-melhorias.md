# biblio — melhorias medidas (noite de 2026-09-07/08)

Investigação sobre **acelerar** e **baratear em token** o biblio, sem perder função.
Tudo medido no acervo real ELE085 (171 docs: 14 PDF de slide + vault Obsidian).

Eval de recuperação: 25 consultas com doc(s) aceitável(is) conhecido(s)
(`scratchpad/ev.py`). `recall@1` = doc certo em 1º; `recall@3` = doc certo no top-3.

---

## Implementado nesta noite (medido, commitado)

### 1. Bônus de heading no ranking — `recall@1 56% → 80%`, `recall@3 80% → 92%`

O maior ganho, e o mais barato. Uma fatia cujo **título** casa com palavras da
pergunta sobe no ranking (bônus proporcional a `|termos ∩ heading| / |termos|`).

Antes, uma pergunta específica ("o que é o escorregamento") era vencida pela aula
que cobre 40 tópicos ou pela nota-índice que cita todos os termos. Agora a nota
atômica **"Escorregamento"** ganha por casar o título.

`feat: bonus de heading no ranking da busca` · constante `BONUS_HEADING = 0.03`
em `search.py` (0.02–0.04 dão o mesmo resultado no eval).

### 2. `_extrair` tolerante — resumos que se perdiam

`qwen3:1.7b` às vezes escreve `TERMOS:` no meio do parágrafo do resumo em vez de
numa linha nova. O parser antigo (linha começando com `TERMOS:`) engolia os
termos no resumo — 4 de 171 documentos (~2%) ficaram sem a linha `**Termos:**`.
Parser novo acha `TERMOS:` em qualquer posição, aceita `**negrito**` e lista com
`-`. `fix: _extrair tolera TERMOS no meio do paragrafo`.

### 3. qwen3 não raciocina + modelo menor — resumo `~180s → ~40s/doc`

(feito antes, recapitulando) `"think": false` não desliga o CoT do qwen3;
`/no_think` + `num_predict=400` + `qwen3:1.7b` + amostra 6k. Backfill dos 171
resumos: **48 min** (era projetado em 9 h com o 4b).

### 4. Heading de slide repetido → uma fatia só — **43% menos fatias nos decks**

Slide deck repete `## Tema` em cada slide do tópico. `slice.py` abria uma fatia
por ocorrência: **197 das 450 fatias (43%)** do acervo eram nome repetido
(`aula-6`: 39 de 47). Agora heading igual ao anterior — mesmo com caixa/pontuação
diferente do OCR (compara por slug) — continua a fatia atual.
**`aula-6`: 47 → 26 fatias.** Menos chunks no índice, menos quase-duplicatas no
ranking, `**Secoes:**` legível. `feat: heading repetido de slide vira uma fatia so`.

### 5. `LIMIAR_CARACTERES` 200 → 120, `INDEX.md` enxuto, aviso de colisão de slug

Detalhados em A, D e G abaixo.

---

## Proposto — ordenado por valor / esforço

(A, D, G foram implementados nesta noite e ficam aqui com a medição que os motivou.)

### A. Ingestão de slides: `LIMIAR_CARACTERES` alto demais — **IMPLEMENTADO**

Medição: das **182 páginas** que a triagem mandou para OCR nos 14 PDFs,
**108 (59%) têm 120–199 caracteres de texto nativo** — logo abaixo do corte de
200. E esse texto nativo **é o conteúdo do slide** (bullets, e as equações, ainda
que com a fonte matemática embaralhada). O OCR dessas páginas relê os mesmos
bullets e gasta ~8 s cada.

Baixado `LIMIAR_CARACTERES` 200 → 120. Medido numa aula OCR-pesada (Aula 1):
conversão **144 s → 82 s (−43%)**, e com *mais* texto indexado (12,7k vs 11,2k
ch) — o nativo dessas páginas rendia mais que o OCR. `perf: LIMIAR 120`.

Melhoria futura mais fina: OCR só se nativo `< 80` **ou** se >40% das páginas do
documento cairiam em OCR (aí é escaneado de verdade, não slide).

### B. OCR em lote — ganho pequeno, não vale agora

`convert._converter_com_docling` faz **uma chamada `convert()` por página**.
Testado: juntar as páginas de OCR num PDF só e chamar `convert()` uma vez,
separando por `page_no` — **1,3× mais rápido** (79 s → 61 s em 10 páginas),
saída idêntica. O custo real é o OCR em si, não o overhead por chamada. Fica
anotado; combinar com paralelismo entre documentos (ProcessPool, 8 núcleos) seria
o ganho grande, mas cada worker recarrega os modelos do Docling.

### C. Notas-índice (MOC) poluindo a busca — `recall@1 +8 pontos` sozinho

`moc-aula-*`, `conceitos`, `vocabulario` são mapas de navegação: citam todos os
termos, casam com tudo. Excluí-los do ranking padrão deu +8 em `recall@1` isolado
(o bônus de heading já cobre a maior parte disso, mas são ortogonais).

- **Ação:** `_meta.yaml` ganha `tipo: indice` quando o documento é
  majoritariamente lista de links / headings; a busca os rebaixa (não exclui —
  ainda aparecem se nada melhor casar). Detecção: 1 fatia + densidade alta de
  `[[wikilink]]` ou de linhas que são só heading.

### D. `INDEX.md` enxuto — **IMPLEMENTADO (parcial)**

Nunca é lido inteiro, mas o `grep -A4` do caminho-de-fallback despeja a linha
`**Secoes:**` com **40 slugs** para um documento grande (20% do arquivo).

`**Secoes:**` agora limitada a 8 nomes + "… (+N)". `perf: INDEX.md enxuto`.
A linha `**Termos:**` (42% do arquivo) fica — é a rede de segurança e cada termo
puxa seu peso no `grep`.

### E. Custo de carga do modelo por busca — **~2–4 s/invocação**

Todo `biblio search` recarrega o `SentenceTransformer` (~90 MB). Para o uso "faço
5 perguntas numa sessão de estudo" isso é 5×.

- **Ação (opt-in):** `biblio serve` — daemon local que mantém o modelo quente;
  `biblio search` fala com ele por socket e cai para o modo atual se não houver
  daemon. Mantém "sem servidor" como padrão.
- **Alternativa barata:** `biblio search` aceita várias consultas numa chamada
  (`--and`), amortizando a carga.

### F. `biblio search --peek` — devolver 1 linha de contexto

Hoje: busca devolve ponteiro → agente faz `Read(offset, limit)` (~500 tokens).
Com `--peek`: a saída inclui a **primeira linha** de cada fatia (~1 frase). Para
pergunta factual simples o agente responde sem o `Read`.

- **Trade:** +~30 tokens/resultado na saída da busca, −~500 quando evita o `Read`.
- Mantém "ponteiro, nunca corpo" como **padrão**; `--peek` é escolha de quem chama.

### G. Colisão de slug — **avisar: IMPLEMENTADO**

`Aula 1.pdf` e `aula-1.md` → mesmo slug → o segundo sobrescrevia o primeiro em
silêncio. Agora `pipeline._processar_um` avisa quando a pasta já existe com uma
`origem` diferente. Falta o passo (b): sufixar (`…-2`) em vez de sobrescrever —
precisa decidir qual fonte ganha, então fica proposto.

### H. Peso por raridade do termo (IDF) no bônus de heading

As 2 consultas que ainda erram no eval: "escorregamento" perde para
"conjugado-máximo-do-motor-de-indução" porque casa 2 tokens comuns (`motor`,
`inducao`) contra 1 raro (`escorregamento`). Pesar cada token do heading por
`log(N/df)` (df = nº de docs cujo heading tem o token) resolveria. Precisa de uma
tabela de `df` — barata de montar no `index.py` e guardar no `config` do banco.

---

## Rejeitado

- **`cap_doc` (máx N fatias por documento no resultado)** — testado, não melhorou
  além do bônus de heading e às vezes piorou `recall@1`. O bônus de heading já
  diversifica na prática.
- **`bonus_doc_slug` (casar com o nome da pasta além do heading)** — mesmo
  resultado que o bônus de heading sozinho; nome da pasta é derivado do heading,
  então é redundante.
- **Trocar RRF por normalização score** — RRF é robusto e o problema não era a
  fusão, era não ter sinal nenhum de "esta fatia é *sobre* isso". O heading deu
  esse sinal.

---

## Números de referência (acervo ELE085, CPU 8 núcleos, sem GPU)

| operação | antes | depois desta noite |
|---|---|---|
| recall@1 / recall@3 (eval 25q) | 56% / 80% | **80% / 92%** |
| resumo por documento | ~180 s (qwen3:4b) | ~40 s (qwen3:1.7b) |
| backfill 171 resumos | ~9 h projetado | **48 min** |
| conversão de aula OCR-pesada (Aula 1) | 144 s | **82 s** (LIMIAR 120) |
| ingestão dos 14 PDFs (478 pág) | ~38 min | ~28 min |
| fatias de `aula-6` | 47 | **26** (dedup de heading) |
| `**Secoes:**` de uma aula de 40 fatias | 40 slugs | 8 + "(+32)" |
| busca (custo em token, 3 ponteiros) | ~60 tokens | inalterado |

## Ainda em aberto (proposto, não feito)

- **C** notas-índice com flag `tipo: indice` (o bônus de heading já cobre a maior parte)
- **E** `biblio serve` — daemon que mantém o modelo quente (~2–4 s/busca hoje)
- **F** `biblio search --peek` — 1 linha de contexto para pular o `Read`
- **H** peso por raridade (IDF) no bônus de heading — resolve as 2 consultas que ainda erram
- **G(b)** sufixar em vez de sobrescrever na colisão de slug
- **B** paralelismo de OCR entre documentos
