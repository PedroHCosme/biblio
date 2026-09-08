# benchmark

Reproduces the numbers in the main README's **Benchmark** section.

## Corpus

- **PDF:** Spong, *Robot Modeling and Control* — 419 pages, ~211k tokens of
  extractable text. Not redistributed here; point `01_ingest.py` at your own copy.
- **MD:** `inverse-kinematics.md` — the English Wikipedia article "Inverse
  kinematics" (CC BY-SA), fetched and wrapped as Markdown.

Machine for the recorded runs: Windows, 8-core CPU, no GPU.

## Scripts

| file | what it measures |
|---|---|
| `01_ingest.py` | one-time ingestion: wall time, slice/chunk count, db size, LLM tokens (0) |
| `02_token_cost.py` | input tokens to answer one question — biblio vs pasting the doc (uses `tiktoken` `cl100k_base`) |
| `03_qa_quality.py` | real answers from `qwen3:1.7b` given three context strategies: first-N-tokens, keyword grep, biblio slice |

```bash
pip install tiktoken
python 01_ingest.py        # edit the PDF path first
python 02_token_cost.py
python 03_qa_quality.py    # needs Ollama + qwen3:1.7b
```

## Recorded results

- `results_token_cost.json` — per-question token cost, ~500 tokens median
- `results_qa.txt` — the qwen3 answers; biblio slice gets the DH parameters right,
  the 1,275-token grep window gets them confidently wrong

Headline: ingestion **9.5 min / 0 LLM tokens**; then **~500 tokens/question**
(~0.1 s warm search) vs **211k** to paste the book (doesn't fit) or **~16k** to
paste the relevant chapter.
