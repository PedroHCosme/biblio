"""Robustness fixes: partial runs stay visible, more corpora get listed."""
import importlib
import os
import sys

import numpy as np
import pytest

from biblio import cli, ollama, pipeline, skill
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


def test_ingest_skips_excluded_files_and_reports_them(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "keep.md").write_text("# Scope\n" + "technical text. " * 40, encoding="utf-8")
    (src / "huge.md").write_text("# Big\n" + "text. " * 40, encoding="utf-8")
    out = tmp_path / "lib"
    msgs = []

    count = pipeline.ingest(src, output=out, exclude=frozenset({src / "huge.md"}),
                            warn=msgs.append)

    assert (out / "keep").is_dir()
    assert not (out / "huge").exists()
    assert count["skipped"] == 1
    assert any("over OCR budget" in m for m in msgs)
    assert any("huge" in m for m in msgs)


@pytest.fixture
def stub_heavy(monkeypatch):
    """Keep CLI add tests off the real model and the real ~/.claude skill dir."""
    monkeypatch.setattr("biblio.pipeline.embed.vectorize",
                        lambda texts: np.zeros((len(texts), 384), dtype="float32"))
    monkeypatch.setattr("biblio.cli.skill.install", lambda *a, **k: None)
    monkeypatch.setattr("biblio.cli.index.generate", lambda *a, **k: None)
    monkeypatch.setattr("biblio.version_check.check", lambda *a, **k: None)


def test_dry_run_prints_estimate_and_writes_nothing(tmp_path, capsys, stub_heavy):
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.md").write_text("# x\ny", encoding="utf-8")
    _blank_pdf(src / "big.pdf", 4)
    out = tmp_path / "lib"

    rc = main(["--out", str(out), "add", str(src), "--dry-run", "--max-ocr-pages", "2"])

    assert rc == 0
    assert not out.exists()  # no bibliotheca created
    report = capsys.readouterr().out
    assert "OCR pages total: 4" in report
    assert "big" in report and "Over --max-ocr-pages (2)" in report


def test_add_yes_skips_over_cap_file_processes_the_rest(tmp_path, capsys, stub_heavy):
    src = tmp_path / "src"
    src.mkdir()
    (src / "keep.md").write_text("# Scope\n" + "technical text. " * 40, encoding="utf-8")
    _blank_pdf(src / "big.pdf", 4)
    out = tmp_path / "lib"

    rc = main(["--out", str(out), "add", str(src), "--yes", "--max-ocr-pages", "2"])

    assert (out / "keep").is_dir()
    assert not (out / "big").exists()
    assert "skipped (over OCR budget)" in capsys.readouterr().out
