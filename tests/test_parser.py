import pytest

from fci_breeds.models import INDEX_URL, MATRIX_URL
from fci_breeds.parser import ParseError, enrich_detail, group_links, parse_breeds


def test_poodle_grouping(matrix):
    poodle = matrix[172]
    assert poodle.name == "CANICHE"
    assert poodle.english_name == "POODLE"
    assert [v.size for v in poodle.varieties] == ["Standard", "Medium size", "Miniature", "Toy"]
    for size in poodle.varieties:
        assert len(size.subvarieties) == 3
        groups = {frozenset(s.colors) for s in size.subvarieties}
        assert groups == {
            frozenset(["Brown", "Black", "White"]),
            frozenset(["Grey", "Fawn"]),
            frozenset(["Other colours"]),
        }
        assert len({s.cacib_group_id for s in size.subvarieties}) == 3


def test_dachshund_combinations(matrix):
    dog = matrix[148]
    assert [v.size for v in dog.varieties] == ["Standard", "Miniature", "Rabbit"]
    for size in dog.varieties:
        assert {s.coat for s in size.subvarieties} == {
            "Long-haired",
            "Smooth-haired",
            "Wire-haired",
        }


def test_named_varieties(matrix):
    assert [v.label for v in matrix[15].varieties] == [
        "Groenendael",
        "Laekenois",
        "Malinois",
        "Tervueren",
    ]
    assert {v.coat for v in matrix[218].varieties} == {"Long-haired", "Smooth-haired"}


def test_shared_awards(matrix):
    dane = matrix[235].varieties
    assert [v.code for v in dane] == list("abcdef")
    assert dane[0].cacib_group_id == dane[1].cacib_group_id
    assert dane[2].cacib_group_id == dane[3].cacib_group_id == dane[4].cacib_group_id
    assert len({v.cacib_group_id for v in dane}) == 3
    assert len(dane[2].source_labels) == 3
    puli = matrix[55].varieties
    assert len(puli) == 5
    assert len({v.cacib_group_id for v in puli}) == 2


def test_blank_placeholder_and_inherited_award(matrix):
    assert matrix[109].varieties[0].label == ""
    assert matrix[109].varieties[0].code == "a"
    assert matrix[109].varieties[0].cacib_group_id == matrix[109].cacib_group_id
    assert all(v.cacib_group_id == matrix[167].cacib_group_id for v in matrix[167].varieties)


def test_group_catalogue(html):
    links = group_links(html("index"))
    assert set(links) == set(range(1, 11))
    dogs = {b.fci_id: b for b in parse_breeds(html("group1"), links[1], group=1)}
    assert dogs[293].group == 1
    assert dogs[293].country == "AUSTRALIA"
    assert dogs[293].section == "Section 1 : Sheepdogs"
    assert dogs[293].varieties == []
    assert dogs[277].english_name == "CROATIAN SHEPHERD DOG"


def test_provisional_detail(html):
    dog = next(
        b for b in parse_breeds(html("index"), INDEX_URL, provisional=True) if b.fci_id == 378
    )
    enrich_detail(dog, html("provisional"))
    assert dog.group == 2
    assert dog.recognition_status == "provisional"
    assert dog.country == "NORTH MACEDONIA"
    assert dog.cacib_group_id is None
    assert dog.english_name == "MACEDONIAN SHEPHERD DOG KARAMAN"


def test_accents_and_parentheses(matrix, html):
    assert matrix[173].name == "CÃO DA SERRA DA ESTRELA"
    dog = next(b for b in parse_breeds(html("group1"), INDEX_URL, group=1) if b.fci_id == 38)
    assert dog.name == "WELSH CORGI (CARDIGAN)"


def test_reject_missing_groups(html):
    with pytest.raises(ParseError, match="ten FCI groups"):
        group_links(html("index").replace("Group 10", "Missing group"))


def test_reject_empty_page():
    with pytest.raises(ParseError, match="No breeds"):
        parse_breeds("<html>Temporarily unavailable</html>", MATRIX_URL)


def test_reject_changed_variety_markup(html):
    with pytest.raises(ParseError, match="Unrecognized variety"):
        parse_breeds(html("matrix").replace("a) Standard", "SIZE: Standard"), MATRIX_URL)


def test_reject_unknown_marker(html):
    with pytest.raises(ParseError, match="Unknown"):
        parse_breeds(html("matrix").replace(">*<", ">NEW<"), MATRIX_URL)


def test_working_trial_meanings():
    from fci_breeds.models import TRIAL_MEANINGS

    assert "applied" in TRIAL_MEANINGS["(*)"]
    assert "Nordic" in TRIAL_MEANINGS["(**)"]


def test_detail_name_and_source_group_order(html, matrix):
    dog = matrix[172]
    enrich_detail(dog, html("poodle"))
    assert dog.english_name == "POODLE"
    assert dog.group == 9
    # Detail enrichment must not replace the authoritative matrix grouping/order.
    assert dog.varieties[0].subvarieties[0].label == "Other colours"


def test_orphan_subvarieties_rejected(html):
    malformed = html("matrix")
    # Insert an unrelated row between the first parent and its nested table.
    from bs4 import BeautifulSoup

    doc = BeautifulSoup(malformed, "html.parser")
    container = doc.select_one(".sousvarietes").find_parent("tr")
    container.insert_before(BeautifulSoup("<tr><td>Unexpected row</td></tr>", "html.parser"))
    with pytest.raises(ParseError, match="Orphan subvarieties"):
        parse_breeds(str(doc), MATRIX_URL)
