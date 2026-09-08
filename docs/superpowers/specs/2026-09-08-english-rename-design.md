# Rename Codebase from Portuguese to English

**Date:** 2026-09-08
**Status:** Approved
**Scope:** All Python identifiers, docstrings, comments, CLI/GUI text, agent instructions, and persisted data keys.

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Approach | Big-bang (single commit) | Pre-1.0, single contributor, no external API consumers |
| Package name | Keep `biblio` | Product name, not a variable |
| Concept name | Keep `bibliotheca` | Product identity |
| UI language | English | PEP 8 and international reach |
| Agent text (SKILL.md, CLAUDE.md) | English | Claude works better with English instructions |
| Ollama prompt | Keep Portuguese | Prompt is internal; marcadores RESUMO:/TERMOS: and parser stay as-is |
| Persisted data keys | Migrate to English | Full consistency |
| Migration strategy | Automatic | `meta.read()` translates old keys and forces reindexation |
| Version | 0.2.0 | Breaking change in data format, pre-1.0 minor bump |
| Commit attribution | No co-authored-by | User preference |

## What Changes

- All Python identifiers (functions, variables, parameters, constants, classes, properties)
- All docstrings and comments
- All CLI help text, messages, prompts
- All GUI labels and messages
- Skill text (SKILL.md) and generated CLAUDE.md
- Persisted data keys (_meta.yaml, SQLite columns, frontmatter keys)
- Test function names and test file names
- Version bump to 0.2.0

## What Does NOT Change

- Package name: `biblio`
- Concept: `bibliotheca`
- Ollama summarization prompt (Portuguese, with RESUMO:/TERMOS: markers)
- Test corpus text (Portuguese technical content — it's the real domain)
- Portuguese stopwords in `search.py` (linguistic data, not code)
- Module file names (already English or universal: `triage.py`, `slice.py`, `meta.py`, etc.)

## Translation Map — Public Identifiers

### biblio/meta.py

| Portuguese | English |
|---|---|
| `hash_arquivo()` | `hash_file()` |
| `ler()` | `read()` |
| `escrever()` | `write()` |
| `ja_processado()` | `already_processed()` |
| `novo()` | `new_record()` |
| YAML keys: `origem, formato, paginas, rota, data, qualidade, falhou, resumo, fatias, termos` | `source, format, pages, route, date, quality, failed, summary, slices, terms` |
| value `"pendente"` | `"pending"` |

### biblio/embed.py

| Portuguese | English |
|---|---|
| `MODELO, PREFIXO_CONSULTA, PREFIXO_DOC, JANELA, SOBREPOSICAO` | `MODEL, QUERY_PREFIX, DOC_PREFIX, WINDOW, OVERLAP` |
| `janelas()` | `windows()` |
| `chunks_do_documento()` | `doc_chunks()` |
| `vetorizar()` | `vectorize()` |
| `vetorizar_consulta()` | `vectorize_query()` |
| dict keys: `texto, linha_ini, linha_fim, arquivo, secao` | `text, line_start, line_end, file, section` |

### biblio/slice.py

| Portuguese | English |
|---|---|
| `PISO, TETO` | `FLOOR, CEILING` |
| `Fatia` (class) | `Slice` |
| `_Bruta` (class) | `_RawSection` |
| fields: `ordem, secao, nivel, texto, pagina_ini, pagina_fim, pai, sufixo, nome` | `order, section, level, text, page_start, page_end, parent, suffix, name` |
| `fatiar()` | `slice_doc()` |
| param `com_paginas` | `with_pages` |

### biblio/triage.py

| Portuguese | English |
|---|---|
| `LIMIAR_CARACTERES` | `CHAR_THRESHOLD` |
| `rotear_pagina()` | `route_page()` |
| `triar()` | `triage()` |
| route keys: `"nativa", "complexa"` | `"native", "complex"` |

### biblio/normalize.py

| Portuguese | English |
|---|---|
| `LIMIAR_REPETICAO, MAX_CARACTERES_CABECALHO` | `REPETITION_THRESHOLD, MAX_HEADER_CHARS` |
| `normalizar()` | `normalize()` |

### biblio/db.py

| Portuguese | English |
|---|---|
| `conectar()` | `connect()` |
| `substituir_documento()` | `replace_document()` |
| `buscar_fts()` | `search_fts()` |
| `buscar_vetorial()` | `search_vector()` |
| `detalhes()` | `details()` |
| SQL columns: `chave, valor, secao, linha_ini, linha_fim, texto, vetor` | `key, value, section, line_start, line_end, text, vector` |

### biblio/paths.py

| Portuguese | English |
|---|---|
| `BIBLIOTHECA_PADRAO, REGISTRO` | `DEFAULT_BIBLIOTHECA, REGISTRY` |
| `raiz()` | `root()` |
| `registrar()` | `register()` |
| `conhecidas_bibliotheca()` | `known_bibliothecas()` |
| `todas()` | `all_libs()` |

### biblio/search.py

| Portuguese | English |
|---|---|
| `buscar()` | `search()` |
| `formatar()` | `format_results()` |

### biblio/summarize.py

| Portuguese | English |
|---|---|
| `MAX_AMOSTRA` | `MAX_SAMPLE` |
| `resumir()` | `summarize()` |

### biblio/ollama.py

| Portuguese | English |
|---|---|
| `MODELO, ENDERECO, INSTRUCAO_MANUAL` | `MODEL, ENDPOINT, MANUAL_INSTRUCTIONS` |
| `instalado()` | `installed()` |
| `disponivel()` | `available()` |
| `quer_resumo()` | `wants_summary()` |
| `garantir()` | `ensure()` |
| `gerar()` | `generate()` |

### biblio/convert.py

| Portuguese | English |
|---|---|
| `converter()` | `convert()` |

### biblio/pipeline.py

| Portuguese | English |
|---|---|
| `adicionar()` | `ingest()` |

### biblio/index.py

| Portuguese | English |
|---|---|
| `gerar()` | `generate()` |

### biblio/skill.py

| Portuguese | English |
|---|---|
| `instalar()` | `install()` |

### biblio/gui.py

| Portuguese | English |
|---|---|
| `subir()` | `launch()` |

### biblio/shortcut.py

| Portuguese | English |
|---|---|
| `criar()` | `create()` |

### biblio/version_check.py

| Portuguese | English |
|---|---|
| `checar()` | `check()` |

### Tests

| Portuguese | English |
|---|---|
| `test_idempotencia.py` | `test_idempotency.py` |
| All PT fixture and test function names | Translated to English equivalents |

## Automatic Migration of Persisted Data

### _meta.yaml (automatic, transparent)

`meta.read()` applies a key translation map on load. If any key was translated, it deletes the `hash` key (forcing reindexation on the next `biblio add`) and rewrites the file immediately. The second read sees English keys and no hash — no-op.

```python
_KEY_MAP = {
    "origem": "source", "formato": "format", "paginas": "pages",
    "rota": "route", "data": "date", "qualidade": "quality",
    "falhou": "failed", "resumo": "summary", "fatias": "slices",
    "termos": "terms",
}
_ROUTE_MAP = {"nativa": "native", "complexa": "complex"}

def _migrate(data: dict) -> dict:
    for old, new in _KEY_MAP.items():
        if old in data and new not in data:
            data[new] = data.pop(old)
    if "route" in data and isinstance(data["route"], dict):
        for old, new in _ROUTE_MAP.items():
            if old in data["route"]:
                data["route"][new] = data["route"].pop(old)
    if data.get("summary") == "pendente":
        data["summary"] = "pending"
    return data
```

### SQLite (automatic via reindexation)

The migration of _meta.yaml deletes the `hash` key, which causes `already_processed()` to return False. The next `biblio add` reprocesses the document, which drops and recreates the SQLite tables with the new column names. No schema migration code needed.

### Slice frontmatter (automatic via reprocessing)

Slices (.md files) are rewritten whenever a document is reprocessed. The reindexation triggered by meta migration causes slices to be regenerated with the new frontmatter keys.

### INDEX.md and CLAUDE.md (automatic via regeneration)

`biblio index` regenerates these files from the migrated metadata. The next `biblio add` or explicit `biblio index` produces English-keyed output.

## Execution Order

1. Leaf modules (no intra-package dependents): `normalize.py`, `triage.py`, `paths.py`, `meta.py`, `ollama.py`, `version_check.py`, `shortcut.py`
2. Intermediate modules: `embed.py`, `slice.py`, `db.py`, `convert.py`, `summarize.py`
3. Orchestration modules: `search.py`, `index.py`, `skill.py`, `pipeline.py`
4. Interface modules: `cli.py`, `gui.py`
5. Tests: `conftest.py` first (shared fixtures), then each `test_*.py`
6. Benchmark scripts (not part of the package)
7. `pyproject.toml`: version bump to 0.2.0

All changes in a single commit.

## Validation

- All existing tests must pass after the rename
- A test that breaks is a signal of a missed identifier
- Manual smoke test: `biblio add` on a small folder, `biblio search`, `biblio status`
