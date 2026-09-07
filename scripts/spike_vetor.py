"""Quanto custa buscar por força bruta? Decide o backend vetorial (risco #2 do spec)."""
import time
import numpy as np

for n in (10_000, 100_000, 500_000):
    for dim in (384, 1024):
        base = np.random.rand(n, dim).astype("float32")
        base /= np.linalg.norm(base, axis=1, keepdims=True)
        q = base[0]
        t = time.perf_counter()
        for _ in range(10):
            np.argpartition(base @ q, -20)[-20:]
        ms = (time.perf_counter() - t) / 10 * 1000
        print(f"{n:>7} chunks  dim {dim:>4}  {ms:6.1f} ms  {base.nbytes/1e6:6.0f} MB")
