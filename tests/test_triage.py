from biblio.triage import route_page, triage


def test_route_page_low_text_goes_to_ocr():
    assert route_page(n_chars=10, has_table=False) == "ocr"


def test_route_page_lots_of_text_and_clean_is_native():
    assert route_page(n_chars=5000, has_table=False) == "native"


def test_route_page_with_table_goes_to_docling():
    assert route_page(n_chars=5000, has_table=True) == "complex"


def test_page_without_text_gets_ocr_even_with_table_detected():
    assert route_page(n_chars=0, has_table=True) == "ocr"


def test_triage_native_document(native_pdf):
    route = triage(native_pdf)
    assert route["native"] == [1, 2]
    assert route["ocr"] == []


def test_triage_scanned_document(scanned_pdf):
    route = triage(scanned_pdf)
    assert route["ocr"] == [1, 2]
    assert route["native"] == []


def test_triage_mixed_document_separates_by_page(mixed_pdf):
    route = triage(mixed_pdf)
    assert route["native"] == [1, 3]
    assert route["ocr"] == [2]
