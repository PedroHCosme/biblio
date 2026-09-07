# Biblioteca biblio

Esta pasta e um acervo de documentos indexado. **Nao a leia por varredura** — sao
centenas de milhares de tokens. Use `biblio search`, que devolve ponteiros.

Nos comandos abaixo, `--lib` recebe **o caminho desta pasta** — a mesma de onde
voce leu este arquivo. O nome dela tambem serve, se ja for conhecida desta maquina
(`biblio libs`). Usar uma pasta uma vez ja a torna conhecida.

Se `biblio` der "command not found", o executavel existe mas nao esta no PATH
deste shell. Tente por outro shell (no Windows, PowerShell) antes de concluir que
a ferramenta nao esta instalada — e **nao** caia em ler a pasta por varredura, nem
em buscar na web: a resposta esta aqui dentro.

## Protocolo

**1. Comece pela busca, sempre.**

```bash
biblio search "<a pergunta reescrita em termos do dominio>" --lib "<caminho desta pasta>"
```

Reescreva antes de buscar. "Quanto de ferro preciso ancorar?" busca mal;
"comprimento de ancoragem armadura passiva" busca bem.

Cada resultado e uma linha: caminho absoluto, intervalo de linhas, score, heading.

```
C:\\Users\\...\\biblio\\nbr-6118\\09-ancoragem.md:1-84  0.032  9.4 Comprimento de ancoragem
```

**Nunca o conteudo** — isso e proposital.

**2. Leia so o que a busca devolveu, com `offset` e `limit`.**

Para `...09-ancoragem.md:112-195`, use `Read` com `offset=112` e `limit=84`.

**`limit` e a quantidade de linhas — `fim - inicio + 1` — nao a linha final.**
Para `:19-36`, e `offset=19` e `limit=18`.

Nao arredonde o intervalo, nao leia o arquivo inteiro, nao leia os vizinhos "por
garantia". Se as linhas devolvidas nao responderem, busque de novo com outros termos.

**3. Busca vazia? Va para os termos do indice.**

```bash
grep -A4 -i "<termo>" <biblioteca>/INDEX.md
```

A linha `**Termos:**` de cada bloco e a rede de seguranca para identificadores
exatos ("NBR 6118", "9.4.2", nome de peca) que a busca semantica erra.

**4. Nunca leia o `INDEX.md` inteiro.** Duzentos documentos dao 40 mil tokens.
Ele foi escrito para `grep`, nao para leitura.

## Outros comandos

| Comando | Para que |
|---|---|
| `biblio search "x" --doc <nome>` | Restringe a um documento |
| `biblio search "x" --lib <caminho>` | Restringe a uma biblioteca |
| `biblio libs` | Lista as bibliotecas registradas |
| `biblio status` | O que entrou, o que falhou, o que esta pendente |

## Cuidados

- Bloco do `INDEX.md` com **AVISO** de OCR de baixa qualidade: o texto pode estar
  corrompido. Diga isso ao usuario antes de citar numero de la.
- Todo arquivo comeca com frontmatter (`doc`, `secao`, `pai`, e `paginas` quando a
  origem era PDF). Use `paginas` para citar a pagina do original.
- A biblioteca nao guarda o arquivo original; `_meta.yaml` guarda o caminho dele.
