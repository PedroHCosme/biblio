from biblio.search import buscar, formatar, rrf


def test_rrf_soma_as_duas_listas():
    pontos = rrf([[10, 20, 30], [30, 40]])
    assert pontos[30] > pontos[10], "id nas duas listas tem que ganhar do primeiro de uma so"
    assert pontos[10] > pontos[20]


def test_rrf_lista_vazia_nao_quebra():
    assert rrf([[], [7]]) == {7: 1 / 61}


def test_consulta_em_portugues_acha_o_arquivo_certo_no_top3(biblioteca_sintetica):
    achados = buscar("como calcular o comprimento de ancoragem", saida=biblioteca_sintetica, top=3)
    assert any(a["arquivo"] == "09-ancoragem.md" for a in achados), achados


def test_identificador_exato_e_achado_pelo_fts(biblioteca_sintetica):
    # top-3, nao top-1: a posicao exata depende do ranking do modelo, e o requisito
    # e "o FTS resgata o termo literal", nao "o RRF poe em primeiro"
    achados = buscar("inversor de frequencia", saida=biblioteca_sintetica, top=3)
    assert any(a["doc"] == "manual-inversor" for a in achados), achados


def test_filtro_por_documento_restringe(biblioteca_sintetica):
    achados = buscar("aderencia", saida=biblioteca_sintetica, top=5, doc="nbr-7480-aco")
    assert achados and all(a["doc"] == "nbr-7480-aco" for a in achados)


def test_um_resultado_por_arquivo(biblioteca_sintetica):
    achados = buscar("ancoragem aderencia concreto", saida=biblioteca_sintetica, top=5)
    caminhos = [a["caminho"] for a in achados]
    assert len(caminhos) == len(set(caminhos))


def test_saida_traz_ponteiro_e_nunca_o_corpo(biblioteca_sintetica):
    achados = buscar("comprimento de ancoragem", saida=biblioteca_sintetica, top=3)
    texto = formatar(achados)
    assert ".md:" in texto
    assert "resistencia de aderencia de calculo" not in texto, "vazou conteudo na saida"
    assert max(len(l) for l in texto.splitlines()) < 200, "linha longa demais"


def test_caminho_devolvido_e_absoluto_e_existe(biblioteca_sintetica):
    from pathlib import Path
    achado = buscar("comprimento de ancoragem", saida=biblioteca_sintetica, top=1)[0]
    caminho = Path(achado["caminho"])
    assert caminho.is_absolute() and caminho.exists()


def test_busca_cobre_duas_bibliotecas(biblioteca_sintetica, biblioteca_secundaria):
    """Spec 6.0: a segunda biblioteca nao pode falhar em silencio."""
    consulta = "fatigue of welded joints under cyclic loading"
    achados = buscar(consulta, saida=[biblioteca_sintetica, biblioteca_secundaria], top=3)
    assert any(a["doc"] == "artigo-fadiga" for a in achados), achados


def test_lib_restringe_a_uma_biblioteca(biblioteca_sintetica, biblioteca_secundaria):
    achados = buscar("fatigue welded joints", saida=biblioteca_sintetica, top=3)
    assert all(a["doc"] != "artigo-fadiga" for a in achados)
