from biblio.slice import PISO, TETO, fatiar


def test_uma_fatia_por_heading():
    md = "# Um\n" + "a" * 500 + "\n# Dois\n" + "b" * 500
    fatias = fatiar(md)
    assert [f.secao for f in fatias] == ["Um", "Dois"]
    assert [f.nome for f in fatias] == ["01-um.md", "02-dois.md"]


def test_piso_secao_curta_gruda_na_proxima():
    md = "# Curta\ncorpo minusculo\n# Grande\n" + "b" * (PISO + 100)
    fatias = fatiar(md)
    assert len(fatias) == 1
    assert "corpo minusculo" in fatias[0].texto
    assert "# Grande" in fatias[0].texto


def test_piso_secao_curta_no_fim_gruda_na_anterior():
    md = "# Grande\n" + "a" * (PISO + 100) + "\n# Curta\nfim"
    fatias = fatiar(md)
    assert len(fatias) == 1
    assert "fim" in fatias[0].texto


def test_teto_secao_longa_quebra_em_paragrafo_com_sufixo():
    paragrafo = "x" * 1000 + "\n\n"
    md = "# Longa\n" + paragrafo * 12  # ~12000 caracteres, acima do teto
    fatias = fatiar(md)
    assert len(fatias) > 1
    assert [f.nome for f in fatias][:2] == ["01-longa-a.md", "01-longa-b.md"]
    assert all(len(f.texto) <= TETO * 1.1 for f in fatias)


def test_pai_aponta_para_o_heading_ancestral():
    md = ("# Capitulo\n" + "a" * 500 + "\n## Secao\n" + "b" * 500)
    fatias = fatiar(md)
    assert fatias[0].pai is None
    assert fatias[1].pai == "01-capitulo.md"


def test_paginas_vem_do_marcador_e_o_marcador_sai_do_texto():
    md = "<!-- pag 5 -->\n# Titulo\n" + "a" * 500 + "\n<!-- pag 7 -->\n" + "b" * 100
    fatia = fatiar(md)[0]
    assert fatia.pagina_ini == 5
    assert fatia.pagina_fim == 7
    assert "<!-- pag" not in fatia.texto


def test_texto_antes_do_primeiro_heading_nao_e_perdido():
    md = "preambulo importante\n" + "a" * 500 + "\n# Primeiro\n" + "b" * 500
    fatias = fatiar(md)
    assert "preambulo importante" in fatias[0].texto


def test_documento_sem_heading_vira_partes_numeradas():
    """Caso tipico do .txt: sem estrutura, cada pedaco do teto e uma fatia propria."""
    md = ("y" * 1000 + "\n\n") * 200  # ~200 mil caracteres; com TETO=8000 dao 29 fatias
    nomes = [f.nome for f in fatiar(md)]
    assert len(nomes) > 26, "o sufixo alfabetico teria estourado aqui"
    assert nomes[:2] == ["01-parte.md", "02-parte.md"]
    assert len(nomes) == len(set(nomes)), "nome de arquivo repetido sobrescreve fatia"


def test_origem_sem_paginas_nao_inventa_pagina():
    fatia = fatiar("# Titulo\n" + "a" * 500, com_paginas=False)[0]
    assert fatia.pagina_ini is None and fatia.pagina_fim is None
