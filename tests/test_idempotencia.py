import pytest

from biblio.pipeline import adicionar


@pytest.fixture
def biblioteca_ingerida(tmp_path, pdf_nativo):
    saida = tmp_path / "lib"
    adicionar(pdf_nativo, saida=saida)
    return saida, pdf_nativo


def _assinatura(pasta):
    return {p.name: (p.stat().st_mtime_ns, p.read_bytes())
            for p in sorted(pasta.rglob("*")) if p.is_file() and p.suffix != ".db"}


def test_segunda_execucao_pula_o_documento(biblioteca_ingerida):
    saida, pdf = biblioteca_ingerida
    assert adicionar(pdf, saida=saida) == {"ok": 0, "pulado": 1, "falhou": 0}


def test_segunda_execucao_nao_reescreve_arquivo_nenhum(biblioteca_ingerida):
    saida, pdf = biblioteca_ingerida
    antes = _assinatura(saida)
    adicionar(pdf, saida=saida)
    assert _assinatura(saida) == antes


def test_force_reprocessa(biblioteca_ingerida):
    saida, pdf = biblioteca_ingerida
    assert adicionar(pdf, saida=saida, force=True)["ok"] == 1


def test_reprocessar_nao_duplica_chunks_no_banco(biblioteca_ingerida):
    from biblio import db
    saida, pdf = biblioteca_ingerida
    con = db.conectar(saida)
    antes = con.execute("SELECT count(*) FROM chunks").fetchone()[0]
    con.close()
    adicionar(pdf, saida=saida, force=True)
    con = db.conectar(saida)
    depois = con.execute("SELECT count(*) FROM chunks").fetchone()[0]
    con.close()
    assert antes == depois > 0


def test_markdown_de_entrada_tambem_e_idempotente(tmp_path):
    """Spec 10: .md entra como caso do teste 5, nao como suite propria."""
    origem = tmp_path / "ja-convertido.md"
    origem.write_text("# Escopo\n" + "texto tecnico. " * 60, encoding="utf-8")
    saida = tmp_path / "lib"

    assert adicionar(origem, saida=saida)["ok"] == 1
    frontmatter = next((saida / "ja-convertido").glob("[0-9]*.md")).read_text(
        encoding="utf-8")
    assert "paginas:" not in frontmatter, "origem sem paginas nao inventa paginas"
    assert adicionar(origem, saida=saida) == {"ok": 0, "pulado": 1, "falhou": 0}
