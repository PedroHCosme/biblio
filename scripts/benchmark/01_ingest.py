# -*- coding: utf-8 -*-
"""Benchmark: ingesta Spong (PDF, 419 pag) + inverse-kinematics.md em ~/biblio/robotics."""
import time, shutil
from pathlib import Path
import biblio.pipeline
biblio.pipeline.ollama.disponivel = lambda: False   # sem resumo: mede so o pipeline

from biblio.pipeline import adicionar
from biblio import index

src_pdf = Path(r"C:\Users\Usuario\Downloads\Spong-RobotmodelingandControl.pdf")
src_md = Path.home() / "biblio-benchmark-src" / "inverse-kinematics.md"
out = Path.home() / "biblio" / "robotics"
if out.exists():
    shutil.rmtree(out)

t0 = time.time()
c1 = adicionar(src_pdf, saida=out, device="cpu", perguntar=None,
               avisar=lambda m: print(f"[{time.time()-t0:6.0f}s] {m}", flush=True))
t_pdf = time.time() - t0
c2 = adicionar(src_md, saida=out, perguntar=None, avisar=lambda m: None)
t_all = time.time() - t0
index.gerar(saida=out, resumir_pendentes=False)

import sqlite3
con = sqlite3.connect(out / "biblio.db")
chunks = con.execute("select count(*) from chunks").fetchone()[0]
fat = sum(len(list(p.glob("[0-9]*.md"))) for p in out.iterdir() if p.is_dir())
db_mb = (out / "biblio.db").stat().st_size / 1e6
print(f"\nPDF: {c1}  em {t_pdf:.0f}s")
print(f"MD:  {c2}")
print(f"total {t_all:.0f}s | {fat} fatias | {chunks} chunks | db {db_mb:.1f} MB")
