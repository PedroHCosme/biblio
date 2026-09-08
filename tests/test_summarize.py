from biblio.summarize import _extrair


def test_formato_limpo():
    r, t = _extrair("RESUMO: Um circuito magnetico conduz fluxo.\nTERMOS: relutancia, fmm, fluxo")
    assert r == "Um circuito magnetico conduz fluxo."
    assert t == ["relutancia", "fmm", "fluxo"]


def test_termos_no_meio_do_paragrafo():
    # qwen3:1.7b faz isso na pratica: nao quebra a linha antes de TERMOS
    r, t = _extrair("Controle por numero de polos e uma tecnica. TERMOS: polos, Dahlander, estator")
    assert r == "Controle por numero de polos e uma tecnica."
    assert t == ["polos", "Dahlander", "estator"]


def test_envolto_em_negrito_e_lista():
    r, t = _extrair("**RESUMO:** Fluxo concatenado.\n\n**TERMOS:**\n- fluxo\n- tensao")
    assert r == "Fluxo concatenado."
    assert t == ["fluxo", "tensao"]


def test_sem_formato_nenhum_nao_quebra():
    r, t = _extrair("O documento trata de varias coisas")
    assert r and t == []
