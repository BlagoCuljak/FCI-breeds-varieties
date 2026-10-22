import sys

import pytest

from fci_breeds.cli import main


def test_failed_crawl_preserves_saved_snapshot(monkeypatch, tmp_path):
    target = tmp_path / "snapshot.json"
    target.write_text("previous snapshot")

    def fail(*args):
        raise ValueError("A group page could not be parsed")

    monkeypatch.setattr("fci_breeds.cli.scrape", fail)
    monkeypatch.setattr(sys, "argv", ["fci-breeds", "scrape", "--output", str(target)])
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 1
    assert target.read_text() == "previous snapshot"
