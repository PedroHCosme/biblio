from biblio.slice import FLOOR, CEILING, slice_doc


def test_one_slice_per_heading():
    md = "# Um\n" + "a" * 500 + "\n# Dois\n" + "b" * 500
    slices = slice_doc(md)
    assert [s.section for s in slices] == ["Um", "Dois"]
    assert [s.name for s in slices] == ["01-um.md", "02-dois.md"]


def test_floor_short_section_merges_into_next():
    md = "# Curta\ncorpo minusculo\n# Grande\n" + "b" * (FLOOR + 100)
    slices = slice_doc(md)
    assert len(slices) == 1
    assert "corpo minusculo" in slices[0].text
    assert "# Grande" in slices[0].text


def test_floor_short_section_at_end_merges_into_previous():
    md = "# Grande\n" + "a" * (FLOOR + 100) + "\n# Curta\nfim"
    slices = slice_doc(md)
    assert len(slices) == 1
    assert "fim" in slices[0].text


def test_ceiling_long_section_splits_at_paragraph_with_suffix():
    paragraph = "x" * 1000 + "\n\n"
    md = "# Longa\n" + paragraph * 12
    slices = slice_doc(md)
    assert len(slices) > 1
    assert [s.name for s in slices][:2] == ["01-longa-a.md", "01-longa-b.md"]
    assert all(len(s.text) <= CEILING * 1.1 for s in slices)


def test_parent_points_to_ancestor_heading():
    md = ("# Capitulo\n" + "a" * 500 + "\n## Secao\n" + "b" * 500)
    slices = slice_doc(md)
    assert slices[0].parent is None
    assert slices[1].parent == "01-capitulo.md"


def test_pages_come_from_marker_and_marker_leaves_text():
    md = "<!-- pag 5 -->\n# Titulo\n" + "a" * 500 + "\n<!-- pag 7 -->\n" + "b" * 100
    s = slice_doc(md)[0]
    assert s.page_start == 5
    assert s.page_end == 7
    assert "<!-- pag" not in s.text


def test_text_before_first_heading_is_not_lost():
    md = "preambulo importante\n" + "a" * 500 + "\n# Primeiro\n" + "b" * 500
    slices = slice_doc(md)
    assert "preambulo importante" in slices[0].text


def test_repeated_slide_heading_does_not_split():
    md = ("# Motores\n" + "d" * 500 + "\n"
          "## Circuitos Magneticos\n" + "a" * 300 + "\n"
          "<!-- pag 2 -->\n## circuitos magneticos\n" + "b" * 300 + "\n"
          "<!-- pag 3 -->\n## Circuitos Magneticos.\n" + "c" * 300)
    circ = [s for s in slice_doc(md) if s.section.lower().startswith("circuitos")]
    assert len(circ) == 1
    assert all(x * 50 in circ[0].text for x in "abc")


def test_document_without_heading_becomes_numbered_parts():
    md = ("y" * 1000 + "\n\n") * 200
    names = [s.name for s in slice_doc(md)]
    assert len(names) > 26
    assert names[:2] == ["01-part.md", "02-part.md"]
    assert len(names) == len(set(names))


def test_source_without_pages_does_not_invent_page():
    s = slice_doc("# Titulo\n" + "a" * 500, with_pages=False)[0]
    assert s.page_start is None and s.page_end is None
