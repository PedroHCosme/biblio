# -*- coding: utf-8 -*-
"""Mede o custo por pergunta: sem biblio vs com biblio."""
import os, sys, time, json
os.environ.update(HF_HUB_DISABLE_PROGRESS_BARS="1", TRANSFORMERS_VERBOSITY="error", HF_HUB_OFFLINE="1")
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
from pathlib import Path
import tiktoken
from biblio.search import buscar, formatar
from biblio import skill

enc = tiktoken.get_encoding("cl100k_base")
def tok(s): return len(enc.encode(s))

LIB = Path.home() / "biblio" / "robotics"

PERGUNTAS = [
    "What are the four Denavit-Hartenberg parameters and what does each represent?",
    "What is the difference between forward and inverse kinematics of a manipulator?",
    "How does the manipulator Jacobian relate joint velocities to end-effector velocity?",
    "What is a singular configuration of a robot manipulator?",
    "What is the control law for computed-torque (inverse dynamics) control?",
]

# --- overhead do biblio numa sessao ---
desc = skill.texto_skill().split("\n")[2]          # a linha description, sempre em contexto
corpo = skill.texto_skill()                        # corpo da skill, uma vez por sessao
print(f"skill: description={tok(desc)} tok (sempre) | corpo={tok(corpo)} tok (1x/sessao)")
print()

resultados = []
t_frio = time.time()
for i, q in enumerate(PERGUNTAS):
    t = time.time()
    ach = buscar(q, saida=LIB, top=3)
    dt = time.time() - t
    saida = formatar(ach)
    # o agente le a 1a fatia devolvida
    slice_txt = Path(ach[0]["caminho"]).read_text(encoding="utf-8", errors="replace")
    linhas = slice_txt.split("\n")[ach[0]["linha_ini"]-1: ach[0]["linha_fim"]]
    trecho = "\n".join(linhas)
    custo = tok(saida) + tok(trecho)
    resultados.append({"q": q, "dt": dt, "saida_tok": tok(saida),
                       "trecho_tok": tok(trecho), "custo": custo,
                       "top1": ach[0]["doc"] + "/" + ach[0]["arquivo"],
                       "linhas": f'{ach[0]["linha_ini"]}-{ach[0]["linha_fim"]}'})
    print(f"Q{i+1}: busca {dt:.1f}s | saida {tok(saida)} tok + trecho {tok(trecho)} tok = "
          f"{custo} tok | {ach[0]['doc']}/{ach[0]['arquivo']}:{ach[0]['linha_ini']}-{ach[0]['linha_fim']}")

media = sum(r["custo"] for r in resultados) / len(resultados)
media_dt = sum(r["dt"] for r in resultados) / len(resultados)
print(f"\nmedia por pergunta: {media:.0f} tokens de entrada, {media_dt:.1f}s de busca")
print(f"(1a busca da sessao inclui carga do modelo: {resultados[0]['dt']:.1f}s; demais ~{sum(r['dt'] for r in resultados[1:])/4:.1f}s)")

Path("results_token_cost.json").write_text(json.dumps({
    "skill_desc_tok": tok(desc), "skill_corpo_tok": tok(corpo),
    "por_pergunta": resultados, "media_custo": media, "media_dt": media_dt,
}, indent=2), encoding="utf-8")
