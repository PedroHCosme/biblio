"""O texto que ensina o agente, e a instalacao dele.

A skill vive em ~/.claude/skills e cobre o Claude Code sem o usuario apontar nada.
O CLAUDE.md vive dentro da pasta e cobre a bibliotheca copiada para outra maquina,
o Claude Desktop, o Cowork e o ChatGPT. Mesmo protocolo, dois alcances.
"""
import sys
from pathlib import Path

from biblio.paths import conhecidas_bibliotheca

DESTINO = Path.home() / ".claude" / "skills" / "bibliotheca"
MAX_NOMES = 8  # ponytail: descricao e contexto permanente; nao vire lista de 50 pastas


def _executavel() -> str:
    """Caminho absoluto do `biblio`, para a skill nao depender de PATH.

    Medido na Tarefa 0.0: o shell POSIX do agente pode receber o PATH do Windows
    como UMA entrada so, e ai `biblio` da `command not found` mesmo instalado. O
    agente se recupera trocando de shell, mas gasta duas chamadas para descobrir
    algo que a skill ja sabia na hora de se instalar.

    So a skill leva o caminho: ela e local a maquina e se reescreve a cada
    ingestao. O CLAUDE.md viaja e continua dizendo so `biblio`.
    """
    for candidato in (Path(sys.executable).parent / "Scripts" / "biblio.exe",
                      Path(sys.executable).with_name("biblio")):
        if candidato.exists():
            return f'"{candidato}"'
    return "biblio"  # instalado de outro jeito; que o PATH resolva


# Dois campos: `{comando}` (caminho absoluto na skill, `biblio` no CLAUDE.md) e
# `{escopo}` (vazio na skill, ` --lib <caminho>` no CLAUDE.md).
# ponytail: .format(), entao nao ponha chave literal neste texto.
PROTOCOLO = """\
## Protocolo

**1. Comece pela busca, sempre.**

```bash
{comando} search "<a pergunta reescrita em termos do dominio>"{escopo}
```

Reescreva antes de buscar. "Quanto de ferro preciso ancorar?" busca mal;
"comprimento de ancoragem armadura passiva" busca bem.

Cada resultado e uma linha: caminho absoluto, intervalo de linhas, score, heading.

```
C:\\\\Users\\\\...\\\\biblio\\\\nbr-6118\\\\09-ancoragem.md:1-84  0.032  9.4 Comprimento de ancoragem
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
grep -A4 -i "<termo>" <bibliotheca>/INDEX.md
```

A linha `**Termos:**` de cada bloco e a rede de seguranca para identificadores
exatos ("NBR 6118", "9.4.2", nome de peca) que a busca semantica erra.

**4. Nunca leia o `INDEX.md` inteiro.** Duzentos documentos dao 40 mil tokens.
Ele foi escrito para `grep`, nao para leitura.

## Outros comandos

| Comando | Para que |
|---|---|
| `biblio search "x" --doc <nome>` | Restringe a um documento |
| `biblio search "x" --lib <caminho>` | Restringe a uma bibliotheca |
| `biblio libs` | Lista as bibliothecas registradas |
| `biblio status` | O que entrou, o que falhou, o que esta pendente |

## Cuidados

- Bloco do `INDEX.md` com **AVISO** de OCR de baixa qualidade: o texto pode estar
  corrompido. Diga isso ao usuario antes de citar numero de la.
- Todo arquivo comeca com frontmatter (`doc`, `secao`, `pai`, e `paginas` quando a
  origem era PDF). Use `paginas` para citar a pagina do original.
- A bibliotheca nao guarda o arquivo original; `_meta.yaml` guarda o caminho dele.
"""

CABECALHO_SKILL = """# Bibliotheca de documentos

Acervo local indexado pelo `biblio`. Grande demais para ler: o protocolo abaixo
existe para achar o paragrafo certo sem carregar o acervo.

O caminho abaixo esta completo de proposito: use exatamente como esta, em qualquer
shell. Nao encurte para `biblio` — nem todo shell tem o PATH do Windows.
"""


def _descricao() -> str:
    """A unica linha que fica em contexto o tempo todo, e por ela que o agente decide
    se o acervo responde a pergunta. Os nomes reais das bibliothecas dizem mais que
    qualquer adjetivo: "controle-digital, normas-abnt" e informacao; "documentos
    tecnicos" e um chute que exclui o acervo de historia do usuario.
    """
    nomes = [Path(c).name for c in conhecidas_bibliotheca()[:MAX_NOMES]]
    quais = f" (bibliothecas: {', '.join(nomes)})" if nomes else ""
    return (f"Consultar o acervo de documentos do usuario{quais}. Use sempre que a "
            "pergunta puder ser respondida por um documento do acervo em vez de "
            "conhecimento geral.")


def texto_skill() -> str:
    """Nao e constante: a descricao muda quando o usuario cria uma bibliotheca nova,
    e o caminho do executavel muda de maquina.
    """
    corpo = CABECALHO_SKILL + "\n" + PROTOCOLO.format(comando=_executavel(), escopo="")
    return f"---\nname: bibliotheca\ndescription: {_descricao()}\n---\n\n{corpo}"


def texto_claude_md() -> str:
    """O mesmo protocolo, mas com `--lib` — sem argumento, porque nada aqui depende
    de onde a pasta esta.

    E o que faz "aponte o Claude para esta pasta" significar "consulte esta
    bibliotheca", e nao "consulte todas as registradas nesta maquina".

    **Sem caminho absoluto de proposito.** Gravar aqui o caminho da maquina que
    gerou o arquivo quebraria a pasta no instante em que ela fosse copiada ou
    movida — e quebraria em silencio. O agente sabe de onde leu este arquivo; e
    ele quem preenche o caminho.
    """
    return f"""# Bibliotheca biblio

Esta pasta e um acervo de documentos indexado. **Nao a leia por varredura** — sao
centenas de milhares de tokens. Use `biblio search`, que devolve ponteiros.

Nos comandos abaixo, `--lib` recebe **o caminho desta pasta** — a mesma de onde
voce leu este arquivo. O nome dela tambem serve, se ja for conhecida desta maquina
(`biblio libs`). Usar uma pasta uma vez ja a torna conhecida.

Se `biblio` der "command not found", o executavel existe mas nao esta no PATH
deste shell. Tente por outro shell (no Windows, PowerShell) antes de concluir que
a ferramenta nao esta instalada — e **nao** caia em ler a pasta por varredura.

{PROTOCOLO.format(comando='biblio', escopo=' --lib "<caminho desta pasta>"')}"""


def instalar(avisar=print) -> Path:
    """Sobrescreve a skill instalada. Idempotente, barato, roda a cada ingestao.

    Roda depois de `registrar()`, para que a bibliotheca recem-criada ja apareca na
    descricao.
    """
    DESTINO.mkdir(parents=True, exist_ok=True)
    alvo = DESTINO / "SKILL.md"
    texto = texto_skill()
    if not alvo.exists() or alvo.read_text(encoding="utf-8") != texto:
        alvo.write_text(texto, encoding="utf-8")
        avisar(f"skill instalada em {alvo}")
    return alvo
