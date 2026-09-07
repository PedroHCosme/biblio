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


@pytest.fixture(autouse=True)
def registro_isolado(tmp_path, monkeypatch):
    """Teste nunca escreve no registro real do usuario."""
    monkeypatch.setattr("biblio.paths.REGISTRO", tmp_path / "bibliotecas.txt")


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


def _montar(raiz, nomes):
    """Indexa de verdade — nada de banco falso; o teste 4 valida o modelo escolhido."""
    from biblio import db, embed

    con = db.conectar(raiz)
    for doc in nomes:
        pasta = raiz / doc
        pasta.mkdir()
        for nome, corpo in CORPUS[doc]:
            (pasta / nome).write_text(
                f"---\ndoc: {doc}\nsecao: x\n---\n\n{corpo}\n", encoding="utf-8")
        chunks = embed.chunks_do_documento(pasta)
        db.substituir_documento(con, doc, chunks,
                                embed.vetorizar([c["texto"] for c in chunks]))
    con.close()
    return raiz


@pytest.fixture(scope="session")
def biblioteca_sintetica(tmp_path_factory):
    """Sessao inteira: o modelo de embedding carrega uma vez so."""
    return _montar(tmp_path_factory.mktemp("lib"),
                   ["nbr-6118-concreto", "nbr-7480-aco", "manual-inversor"])


@pytest.fixture(scope="session")
def biblioteca_secundaria(tmp_path_factory):
    """A segunda biblioteca que o usuario cria noutra rodada (spec 6.0)."""
    return _montar(tmp_path_factory.mktemp("lib2"), ["artigo-fadiga"])
