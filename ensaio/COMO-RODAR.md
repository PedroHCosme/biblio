# Ensaio do protocolo (Tarefa 0.0)

Testa a premissa que carrega o projeto inteiro, **antes** de escrever qualquer
código dele: *um agente que ninguém instruiu prefere `biblio search` a ler a pasta?*

Nada aqui é reaproveitado. É ensaio, e é para jogar fora.

## O que está instalado agora

| Onde | O quê |
|---|---|
| `~/.claude/skills/biblioteca/SKILL.md` | A skill de verdade, copiada à mão da Tarefa 2.4 |
| `~/bin/biblio.cmd` | `biblio` **de mentira**: ignora a consulta e imprime três ponteiros fixos |
| `ensaio/acervo-tecnico/` | Quatro fatias, `INDEX.md` e `CLAUDE.md` de uma norma inventada |

## O truque do ensaio

A norma NI-4471 **não existe**. O fator de correção para peça concretada em
posição invertida (**1,35**, e **1,50** para barra acima de 25 mm) não está em
lugar nenhum do mundo além de `03-ancoragem.md`.

Então a resposta é uma prova: quem acerta o número, leu o arquivo. Quem responde
de cabeça, erra ou diz que não sabe — e a premissa caiu.

## Como rodar

Abra um Claude Code **novo**, numa pasta **qualquer** que não seja esta, sem
apontar nada, e pergunte:

> Qual o fator de correção do comprimento de ancoragem para peças pré-moldadas
> concretadas em posição invertida?

Observe sem ajudar:

| O que observar | Resposta boa |
|---|---|
| Chamou `biblio search`? | sim, por conta própria |
| Chamou **antes** de tentar `Glob`/`Grep`/`Read`? | sim |
| Leu só o intervalo devolvido? | `Read` com `offset`/`limit`, não o arquivo inteiro |
| Leu o `INDEX.md` inteiro? | não |
| Respondeu **1,35**? | sim |

## Resultado da rodada 1 (2026-09-07)

**Claude Code, nada apontado: passou.** Skill disparou sozinha, buscou, leu,
respondeu **1,35**. Dois defeitos, os dois corrigidos nos arquivos acima:

1. `biblio: command not found` na primeira chamada — o shell POSIX do Claude Code
   recebe o PATH do Windows como uma entrada só. Corrigido: a skill agora chama
   pelo caminho absoluto.
2. Leu 1-40 em vez de 19-36 — o exemplo do protocolo usava `:1-84`, onde `limit`
   coincide com a linha final, e ensinava a aritmética errada. Corrigido.

**Cowork, nada apontado: foi para a web.** Previsto (não carrega skill, e o
`CLAUDE.md` só entra quando alguém aponta a pasta), mas fica registrado como
limitação declarada.

## Resultado da rodada 2 (2026-09-07) — ensaio encerrado

**Claude Code: limpo.** Uma chamada pelo caminho absoluto, leu `19,36` e `10,14`
exatos, respondeu 1,35 e avisou que a fonte era a NI-4471 e não a NBR 9062 da
pergunta. Os dois defeitos da rodada 1 estão fechados. **Premissa validada.**

**Cowork, pasta apontada: `cat` em tudo.** Respondeu certo, por varredura. Tinha
shell — poderia ter rodado a busca. O `CLAUDE.md` foi lido *dentro* da varredura
que existia para impedir: chegou tarde.

Conclusão registrada no spec §7.3: o que separa os dois veículos é **quando o texto
chega**, não o que ele diz. Onde não há carregamento prévio, o produto é a pasta
fatiada + `INDEX.md` — e um pedido explícito ("use `biblio search` nessa pasta")
devolve o protocolo inteiro.

O ensaio cumpriu o que tinha para cumprir. Pode ser apagado.

## O que fazer com o resultado

| Resultado | Decisão |
|---|---|
| Buscou sozinho e leu só o intervalo | Premissa de pé. Segue para a Tarefa 0.1 |
| Buscou mas leu o arquivo inteiro | O passo 2 do protocolo está frouxo. Reescrever **antes** da Tarefa 2.4 |
| Não buscou | **Parar.** A `description` não ganha a decisão. Testar outras redações aqui, no barato |
| Buscou e se confundiu com os ponteiros | Ajustar o formato da spec §6 — texto, não código |

## Desinstalar

Antes da Fase 1, obrigatoriamente — o `biblio` falso sombreia o de verdade:

```bash
rm ~/bin/biblio.cmd && rm -r ~/.claude/skills/biblioteca && rm -r ensaio
```
