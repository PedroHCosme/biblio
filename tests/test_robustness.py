"""Robustness fixes: partial runs stay visible, more corpora get listed."""
import importlib
import os
import sys

from biblio import pipeline, skill
from biblio.cli import main
from biblio.paths import known_bibliothecas


def _boom(*a, **k):
    raise RuntimeError("boom")


def test_registers_bibliotheca_before_processing(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "_process_one", _boom)
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.md").write_text("# x\n" + "y " * 40, encoding="utf-8")
    out = tmp_path / "lib"

    pipeline.ingest(src, output=out)  # every file fails, loop swallows it

    assert str(out.resolve()) in known_bibliothecas()


def test_description_lists_up_to_twenty_bibliothecas(monkeypatch):
    fake = [f"/x/lib{i:02d}" for i in range(25)]
    monkeypatch.setattr("biblio.skill.known_bibliothecas", lambda: fake)

    d = skill._description()

    assert "lib08" in d  # 9th entry — dropped under the old cap of 8
    assert "lib19" in d  # 20th entry
    assert "lib20" not in d  # 21st — still capped


def test_importing_embed_forces_hub_offline(monkeypatch):
    monkeypatch.delenv("HF_HUB_OFFLINE", raising=False)
    monkeypatch.delenv("HF_HUB_DISABLE_TELEMETRY", raising=False)
    import biblio.embed
    importlib.reload(biblio.embed)
    assert os.environ["HF_HUB_OFFLINE"] == "1"
    assert os.environ["HF_HUB_DISABLE_TELEMETRY"] == "1"


def test_model_retries_online_when_offline_load_fails(monkeypatch):
    import biblio.embed as e
    e._model.cache_clear()
    seen = []

    class FakeST:
        def __init__(self, name):
            seen.append(os.environ.get("HF_HUB_OFFLINE"))
            if len(seen) == 1:
                raise OSError("model not in cache")

    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setattr("sentence_transformers.SentenceTransformer", FakeST)

    e._model()

    assert seen == ["1", None]  # first attempt offline, retry with the var cleared
    assert os.environ["HF_HUB_OFFLINE"] == "1"  # restored afterwards
    e._model.cache_clear()


def test_update_on_windows_prints_command_and_does_not_run(monkeypatch, capsys):
    monkeypatch.setattr(sys, "platform", "win32")
    calls = []
    monkeypatch.setattr("subprocess.run", lambda *a, **k: calls.append(a))

    rc = main(["update"])

    assert rc == 0
    assert calls == []
    out = capsys.readouterr().out
    assert "pip install --upgrade git+https://github.com/PedroHCosme/biblio.git" in out


def _blank_pdf(path, n_pages):
    import pymupdf
    doc = pymupdf.open()
    for _ in range(n_pages):
        doc.new_page()
    doc.save(path)
    doc.close()
    return path


def test_survey_aggregates_ocr_pages_and_flags_over_cap(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "note.md").write_text("# x\ny", encoding="utf-8")
    big = _blank_pdf(src / "big.pdf", 4)      # 4 OCR pages
    small = _blank_pdf(src / "small.pdf", 1)  # 1 OCR page

    report = pipeline.survey(src, max_ocr_pages=2)

    assert report["total_ocr"] == 5
    assert report["by_ext"] == {".md": 1, ".pdf": 2}
    assert set(report["over_cap"]) == {big}
    assert small not in report["over_cap"]
    assert report["max_ocr_pages"] == 2


def test_survey_zero_cap_flags_nothing(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    _blank_pdf(src / "big.pdf", 4)
    assert pipeline.survey(src, max_ocr_pages=0)["over_cap"] == {}
