import pymupdf
import pytest

DENSE_TEXT = ("Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 8)


def _pdf(dest, pages):
    """pages: list of strings; empty string = page without text (simulates scanned)."""
    doc = pymupdf.open()
    for content in pages:
        page = doc.new_page()
        if content:
            page.insert_textbox(pymupdf.Rect(50, 50, 550, 750), content, fontsize=11)
    doc.save(dest)
    doc.close()
    return dest


@pytest.fixture
def native_pdf(tmp_path):
    return _pdf(tmp_path / "native.pdf", [DENSE_TEXT, DENSE_TEXT])


@pytest.fixture
def scanned_pdf(tmp_path):
    return _pdf(tmp_path / "scanned.pdf", ["", ""])


@pytest.fixture
def mixed_pdf(tmp_path):
    return _pdf(tmp_path / "mixed.pdf", [DENSE_TEXT, "", DENSE_TEXT])


@pytest.fixture(autouse=True)
def isolated_registry(tmp_path, monkeypatch):
    """Test never writes to the user's real registry."""
    monkeypatch.setattr("biblio.paths.REGISTRY", tmp_path / "bibliothecas.txt")


@pytest.fixture(autouse=True)
def without_ollama(monkeypatch):
    """Don't call the local model in tests, even if the machine has Ollama running."""
    monkeypatch.setattr("biblio.ollama.available", lambda: False)


CORPUS = {
    "nbr-6118-concreto": [
        ("09-ancoragem.md", "# 9.4 Comprimento de ancoragem\n"
         "O comprimento de ancoragem basico depende da resistencia de aderencia "
         "de calculo entre a barra e o concreto. " * 6),
        ("07-cobrimento.md", "# 7.4 Cobrimento nominal\n"
         "O cobrimento nominal da armadura varia com a classe de agressividade "
         "ambiental. " * 6),
    ],
    "nbr-7480-aco": [
        ("04-ensaios.md", "# 4.3 Ensaio de aderencia\n"
         "Barras nervuradas sao submetidas a ensaio de arrancamento para "
         "verificar a aderencia. " * 6),
    ],
    "manual-inversor": [
        ("02-partida.md", "# 2 Partida suave\n"
         "Configure a rampa de aceleracao do inversor de frequencia para o motor "
         "trifasico. " * 6),
    ],
    "artigo-fadiga": [
        ("03-fadiga.md", "# 3 Fadiga\n"
         "Fatigue life of welded joints under cyclic loading is governed by the "
         "stress range. " * 6),
    ],
}


def _build(root, names):
    """Indexes for real — no fake DB; test 4 validates the chosen model."""
    from biblio import db, embed

    con = db.connect(root)
    for doc in names:
        folder = root / doc
        folder.mkdir()
        for fname, body in CORPUS[doc]:
            (folder / fname).write_text(
                f"---\ndoc: {doc}\nsection: x\n---\n\n{body}\n", encoding="utf-8")
        chunks = embed.doc_chunks(folder)
        db.replace_document(con, doc, chunks,
                            embed.vectorize([c["text"] for c in chunks]))
    con.close()
    return root


@pytest.fixture(scope="session")
def synthetic_bibliotheca(tmp_path_factory):
    """Entire session: the embedding model loads once."""
    return _build(tmp_path_factory.mktemp("lib"),
                  ["nbr-6118-concreto", "nbr-7480-aco", "manual-inversor"])


@pytest.fixture(scope="session")
def secondary_bibliotheca(tmp_path_factory):
    """The second bibliotheca the user creates in another run."""
    return _build(tmp_path_factory.mktemp("lib2"), ["artigo-fadiga"])
