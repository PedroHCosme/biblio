from biblio.normalize import normalize


def test_joins_broken_hyphen():
    text = "O comprimento de anco-\nragem depende da aderencia."
    assert "ancoragem" in normalize(text)


def test_does_not_join_legitimate_compound_hyphen():
    text = "Ensaio guarda-\nRoupa nao existe"
    assert "guarda-\nRoupa" in normalize(text) or "guarda-Roupa" not in normalize(text)


def test_removes_repeated_header_across_pages():
    text = "\n".join(f"ABNT NBR 6118:2023\npage content {i}" for i in range(4))
    output = normalize(text)
    assert "ABNT NBR 6118:2023" not in output
    assert output.count("page content") == 4


def test_preserves_repeated_line_that_is_heading():
    text = "# Doc\n" + "\n".join(f"## Requisitos\nbody {i}" for i in range(4))
    assert normalize(text).count("## Requisitos") == 4


def test_removes_bold_slide_footer():
    text = "\n".join(
        f"# Slide {i}\nslide body {i}\n**Conversores - ELE085**\n**{i}**"
        for i in range(1, 6))
    output = normalize(text)
    assert "ELE085" not in output, "repeated bold footer should be removed"
    assert "**1**" not in output and "\n**2**\n" not in output
    assert output.count("slide body") == 5


def test_legitimate_non_repeated_bold_stays():
    text = "# Doc\n**Importante:** leia isto com atencao antes de comecar"
    assert "**Importante:**" in normalize(text)


def test_removes_standalone_page_number():
    text = "useful text\n42\nother useful text\nPagina 43 de 238\nend"
    output = normalize(text)
    assert "\n42\n" not in output
    assert "Pagina 43 de 238" not in output
    assert "useful text" in output and "end" in output


def test_promotes_hierarchy_when_document_starts_at_level_two():
    text = "## Objetivo\nbody\n### Detalhe\nbody"
    output = normalize(text)
    assert output.startswith("# Objetivo")
    assert "## Detalhe" in output


def test_does_not_touch_hierarchy_when_already_at_level_one():
    text = "# Objetivo\nbody\n## Detalhe\nbody"
    assert normalize(text) == text + "\n"


def test_preserves_page_marker():
    text = "<!-- pag 7 -->\n# Titulo\nbody"
    assert "<!-- pag 7 -->" in normalize(text)
