import pymupdf
import pytest

TEXTO_DENSO = ("Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 8)


def _pdf(destino, paginas):
    """paginas: lista de strings; string vazia = pagina sem texto (finge escaneada)."""
    doc = pymupdf.open()
    for conteudo in paginas:
        pagina = doc.new_page()
        if conteudo:
            pagina.insert_textbox(pymupdf.Rect(50, 50, 550, 750), conteudo, fontsize=11)
    doc.save(destino)
    doc.close()
    return destino


@pytest.fixture
def pdf_nativo(tmp_path):
    return _pdf(tmp_path / "nativo.pdf", [TEXTO_DENSO, TEXTO_DENSO])


@pytest.fixture
def pdf_escaneado(tmp_path):
    return _pdf(tmp_path / "escaneado.pdf", ["", ""])


@pytest.fixture
def pdf_misto(tmp_path):
    return _pdf(tmp_path / "misto.pdf", [TEXTO_DENSO, "", TEXTO_DENSO])
