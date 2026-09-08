from biblio.pipeline import _strip_source_frontmatter


def test_removes_source_frontmatter_and_keeps_body():
    md = "---\ntags: [a/b]\naliases: [x, y]\n---\n\n# Titulo\ncorpo"
    output = _strip_source_frontmatter(md)
    assert not output.startswith("---")
    assert "# Titulo\ncorpo" in output
    assert "*x, y, a/b*" in output, "aliases and tags become searchable line"


def test_no_frontmatter_passes_through():
    md = "# Titulo\ncorpo\n---\nhorizontal divider"
    assert _strip_source_frontmatter(md) == md
