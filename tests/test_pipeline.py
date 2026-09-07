from biblio.pipeline import _sem_frontmatter_de_fonte


def test_remove_frontmatter_de_fonte_e_mantem_o_corpo():
    md = "---\ntags: [a/b]\naliases: [x, y]\n---\n\n# Titulo\ncorpo"
    saida = _sem_frontmatter_de_fonte(md)
    assert not saida.startswith("---")
    assert "# Titulo\ncorpo" in saida
    assert "*x, y, a/b*" in saida, "aliases e tags viram linha pesquisavel"


def test_sem_frontmatter_passa_intacto():
    md = "# Titulo\ncorpo\n---\ndivisor horizontal"
    assert _sem_frontmatter_de_fonte(md) == md
