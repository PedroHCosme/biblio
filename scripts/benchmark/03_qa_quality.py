# -*- coding: utf-8 -*-
"""Q&A real com qwen3:1.7b: mesma pergunta, 3 estrategias de contexto."""
import os, sys, time, json, re
os.environ.update(HF_HUB_DISABLE_PROGRESS_BARS="1", TRANSFORMERS_VERBOSITY="error", HF_HUB_OFFLINE="1")
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
from pathlib import Path
import tiktoken, pymupdf
from biblio.search import buscar
from biblio import ollama

enc = tiktoken.get_encoding("cl100k_base")
tok = lambda s: len(enc.encode(s))
LIB = Path.home() / "biblio" / "robotics"
PDF = Path(r"C:\Users\Usuario\Downloads\Spong-RobotmodelingandControl.pdf")

doc = pymupdf.open(PDF)
FULL = "\n".join(p.get_text() for p in doc)
doc.close()

PROMPT = ("Answer the question using ONLY the context. If the context does not "
          "contain the answer, say \"not in the provided text\".\n\n"
          "Context:\n{ctx}\n\nQuestion: {q}\n\nAnswer:")

PERGUNTAS = [
    ("What are the four Denavit-Hartenberg parameters?", "denavit"),
    ("What is a singular configuration of a manipulator and why does it matter?", "singular"),
]

def ask(ctx, q):
    t = time.time()
    a = ollama.gerar(PROMPT.format(ctx=ctx, q=q), timeout=240, max_tokens=250)
    return a.strip(), time.time() - t, tok(ctx)

out = []
for q, kw in PERGUNTAS:
    print(f"\n{'='*70}\nQ: {q}")

    # 1. naive: primeiras paginas que cabem num modelo local (~3500 tok)
    naive = enc.decode(enc.encode(FULL)[:3500])
    a1, dt1, n1 = ask(naive, q)
    print(f"\n[naive: 1as paginas, {n1} tok, {dt1:.0f}s]\n{a1[:400]}")

    # 2. keyword grep: +-1800 chars da 1a ocorrencia do termo
    m = re.search(kw, FULL, re.I)
    grep = FULL[max(0, m.start()-1800): m.start()+1800] if m else ""
    a2, dt2, n2 = ask(grep, q)
    print(f"\n[keyword grep '{kw}', {n2} tok, {dt2:.0f}s]\n{a2[:400]}")

    # 3. biblio
    ach = buscar(q, saida=LIB, top=1)[0]
    s = Path(ach["caminho"]).read_text(encoding="utf-8", errors="replace").split("\n")
    trecho = "\n".join(s[ach["linha_ini"]-1: ach["linha_fim"]])
    a3, dt3, n3 = ask(trecho, q)
    print(f"\n[biblio {ach['arquivo']}:{ach['linha_ini']}-{ach['linha_fim']}, {n3} tok, {dt3:.0f}s]\n{a3[:400]}")

    out.append({"q": q,
                "naive": {"tok": n1, "s": round(dt1), "a": a1},
                "grep": {"tok": n2, "s": round(dt2), "a": a2},
                "biblio": {"tok": n3, "s": round(dt3), "a": a3}})

Path("results_qa.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
