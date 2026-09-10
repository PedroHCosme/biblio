"""Robustness fixes: partial runs stay visible, more corpora get listed."""
from pathlib import Path

from biblio import pipeline, skill
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
