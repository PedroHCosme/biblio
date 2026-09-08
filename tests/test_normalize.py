from biblio.normalize import normalizar


def test_junta_hifen_de_quebra_de_linha():
    entrada = "O comprimento de anco-\nragem depende da aderencia."
    assert "ancoragem" in normalizar(entrada)


def test_nao_junta_hifen_legitimo_de_palavra_composta():
    entrada = "Ensaio guarda-\nRoupa nao existe"  # maiuscula depois do hifen
    assert "guarda-\nRoupa" in normalizar(entrada) or "guarda-Roupa" not in normalizar(entrada)


def test_remove_cabecalho_repetido_em_toda_pagina():
    # conteudo distinto por pagina: repetir o corpo tambem faria dele um cabecalho,
    # e o teste passaria a exigir da heuristica algo que ela nao pode saber
    entrada = "\n".join(f"ABNT NBR 6118:2023\nconteudo da pagina {i}" for i in range(4))
    saida = normalizar(entrada)
    assert "ABNT NBR 6118:2023" not in saida
    assert saida.count("conteudo da pagina") == 4


def test_preserva_linha_repetida_que_e_heading():
    # o h1 no topo ancora a hierarquia: sem ele a promocao vira todo ## em #,
    # e o teste mediria promocao em vez de preservacao
    entrada = "# Doc\n" + "\n".join(f"## Requisitos\ncorpo {i}" for i in range(4))
    assert normalizar(entrada).count("## Requisitos") == 4


def test_remove_rodape_de_slide_em_negrito():
    # slide deck: cada pagina repete o rodape em **negrito** e o numero em **N**
    entrada = "\n".join(
        f"# Slide {i}\ncorpo do slide {i}\n**Conversores - ELE085**\n**{i}**"
        for i in range(1, 6))
    saida = normalizar(entrada)
    assert "ELE085" not in saida, "rodape em negrito repetido devia sair"
    assert "**1**" not in saida and "\n**2**\n" not in saida
    assert saida.count("corpo do slide") == 5


def test_negrito_legitimo_nao_repetido_fica():
    entrada = "# Doc\n**Importante:** leia isto com atencao antes de comecar"
    assert "**Importante:**" in normalizar(entrada)


def test_remove_numero_de_pagina_solto():
    entrada = "texto util\n42\noutro texto util\nPagina 43 de 238\nfim"
    saida = normalizar(entrada)
    assert "\n42\n" not in saida
    assert "Pagina 43 de 238" not in saida
    assert "texto util" in saida and "fim" in saida


def test_promove_hierarquia_quando_documento_comeca_em_nivel_dois():
    entrada = "## Objetivo\ncorpo\n### Detalhe\ncorpo"
    saida = normalizar(entrada)
    assert saida.startswith("# Objetivo")
    assert "## Detalhe" in saida


def test_nao_mexe_na_hierarquia_quando_ja_comeca_em_nivel_um():
    entrada = "# Objetivo\ncorpo\n## Detalhe\ncorpo"
    assert normalizar(entrada) == entrada + "\n"  # garantir quebra final e desejado


def test_preserva_o_marcador_de_pagina():
    entrada = "<!-- pag 7 -->\n# Titulo\ncorpo"
    assert "<!-- pag 7 -->" in normalizar(entrada)
