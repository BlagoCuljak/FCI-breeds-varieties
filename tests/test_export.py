import csv
import hashlib
import json

import pytest

from fci_breeds.export import export, rows
from fci_breeds.validation import counts, validate


def test_csv_preserves_groups_and_unicode(matrix):
    poodle = list(rows(matrix[172]))
    assert len(poodle) == 12
    assert {r["size"] for r in poodle} == {"Standard", "Medium size", "Miniature", "Toy"}
    assert len(list(rows(matrix[148]))) == 9
    assert list(rows(matrix[173]))[0]["name"] == "CÃO DA SERRA DA ESTRELA"


def test_complete_export(catalogue, tmp_path):
    destination = tmp_path / "dist"
    export(catalogue, destination)
    api = destination / "api/v1"
    data = json.loads((api / "breeds.json").read_text())
    metadata = json.loads((api / "meta.json").read_text())
    assert hashlib.sha256((api / "breeds.json").read_bytes()).hexdigest() == metadata["sha256"]
    with (api / "breeds.csv").open(newline="") as handle:
        csv_rows = list(csv.DictReader(handle))
    assert {int(r["fci_id"]) for r in csv_rows} == {b["fci_id"] for b in data["breeds"]}
    assert len(csv_rows) == counts(catalogue)["leaves"]
    for breed in catalogue.breeds:
        assert json.loads((api / f"breeds/{breed.fci_id}.json").read_text())["breed"] == (
            breed.model_dump(mode="json")
        )
    assert "attachment" in (destination / "_headers").read_text()


def test_failed_validation_preserves_previous_export(catalogue, tmp_path):
    destination = tmp_path / "dist"
    export(catalogue, destination)
    original = (destination / "api/v1/breeds.json").read_bytes()
    catalogue.breeds = catalogue.breeds[:10]
    with pytest.raises(ValueError, match="Incomplete catalogue"):
        export(catalogue, destination)
    assert (destination / "api/v1/breeds.json").read_bytes() == original


def test_count_drop(catalogue):
    newer = catalogue.model_copy(deep=True)
    # Keep reference breeds; remove enough other breeds to exceed the guard.
    newer.breeds = [
        b for b in newer.breeds if b.fci_id <= 345 or b.recognition_status == "provisional"
    ]
    previous = catalogue.model_copy(deep=True)
    previous.breeds += [
        b.model_copy(update={"fci_id": b.fci_id + 1000}) for b in catalogue.breeds[:40]
    ]
    with pytest.raises(ValueError, match="dropped"):
        validate(newer, previous)


def test_duplicate_id(catalogue):
    catalogue.breeds.append(catalogue.breeds[0])
    with pytest.raises(ValueError, match="Duplicate breed IDs"):
        validate(catalogue)


def test_export_removes_obsolete_breed_files(catalogue, tmp_path):
    destination = tmp_path / "dist"
    export(catalogue, destination)
    assert (destination / "api/v1/breeds/1.json").exists()
    catalogue.breeds = [b for b in catalogue.breeds if b.fci_id != 1]
    export(catalogue, destination)
    assert not (destination / "api/v1/breeds/1.json").exists()


def test_csv_quotes_labels(matrix):
    import io

    from fci_breeds.export import CSV_FIELDS

    dog = matrix[172]
    dog.name = 'A "quoted", accented name: Č'
    handle = io.StringIO(newline="")
    writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
    writer.writeheader()
    writer.writerows(rows(dog))
    handle.seek(0)
    decoded = list(csv.DictReader(handle))
    assert decoded[0]["name"] == dog.name
    assert json.loads(decoded[0]["colors"]) == ["Other colours"]
