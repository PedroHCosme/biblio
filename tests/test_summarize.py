from biblio.summarize import _extract


def test_clean_format():
    r, t = _extract("RESUMO: Um circuito magnetico conduz fluxo.\nTERMOS: relutancia, fmm, fluxo")
    assert r == "Um circuito magnetico conduz fluxo."
    assert t == ["relutancia", "fmm", "fluxo"]


def test_terms_mid_paragraph():
    r, t = _extract("Controle por numero de polos e uma tecnica. TERMOS: polos, Dahlander, estator")
    assert r == "Controle por numero de polos e uma tecnica."
    assert t == ["polos", "Dahlander", "estator"]


def test_wrapped_in_bold_and_list():
    r, t = _extract("**RESUMO:** Fluxo concatenado.\n\n**TERMOS:**\n- fluxo\n- tensao")
    assert r == "Fluxo concatenado."
    assert t == ["fluxo", "tensao"]


def test_no_format_does_not_break():
    r, t = _extract("O documento trata de varias coisas")
    assert r and t == []
