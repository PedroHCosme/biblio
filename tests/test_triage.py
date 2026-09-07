from biblio.triage import rotear_pagina, triar


def test_rotear_pagina_pouco_texto_vai_para_ocr():
    assert rotear_pagina(n_caracteres=10, tem_tabela=False) == "ocr"


def test_rotear_pagina_muito_texto_e_limpa_e_nativa():
    assert rotear_pagina(n_caracteres=5000, tem_tabela=False) == "nativa"


def test_rotear_pagina_com_tabela_vai_para_docling():
    assert rotear_pagina(n_caracteres=5000, tem_tabela=True) == "complexa"


def test_pagina_sem_texto_ganha_ocr_mesmo_com_tabela_detectada():
    # densidade manda: pagina escaneada nao tem tabela "de verdade" para o pymupdf
    assert rotear_pagina(n_caracteres=0, tem_tabela=True) == "ocr"


def test_triar_documento_nativo(pdf_nativo):
    rota = triar(pdf_nativo)
    assert rota["nativa"] == [1, 2]
    assert rota["ocr"] == []


def test_triar_documento_escaneado(pdf_escaneado):
    rota = triar(pdf_escaneado)
    assert rota["ocr"] == [1, 2]
    assert rota["nativa"] == []


def test_triar_documento_misto_separa_por_pagina(pdf_misto):
    rota = triar(pdf_misto)
    assert rota["nativa"] == [1, 3]
    assert rota["ocr"] == [2]
