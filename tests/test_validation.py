from app.dadata_client import normalize_query_input, validate_inn, validate_ogrn


def test_valid_inn_10():
    assert validate_inn("7707083893") is True


def test_valid_inn_12():
    assert validate_inn("784806113663") is True


def test_invalid_inn_letters():
    assert validate_inn("770708389X") is False


def test_valid_ogrn_13():
    assert validate_ogrn("1027700132195") is True


def test_valid_ogrn_15():
    assert validate_ogrn("304500116000157") is True


def test_invalid_ogrn():
    assert validate_ogrn("30450011600015") is False


def test_normalize_inn_from_dirty_text():
    query, kind = normalize_query_input("ИНН: 7707-083-893")
    assert query == "7707083893"
    assert kind == "inn"


def test_normalize_ogrn_from_dirty_text():
    query, kind = normalize_query_input("ОГРН 1027 7001 32195")
    assert query == "1027700132195"
    assert kind == "ogrn"


def test_normalize_name():
    query, kind = normalize_query_input('ООО "Ромашка"')
    assert query == 'ООО "Ромашка"'
    assert kind == "name"
