from pathlib import Path

import pytest

from fci_breeds.models import MATRIX_URL
from fci_breeds.parser import parse_breeds

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def html():
    return lambda name: (FIXTURES / f"{name}.html").read_text(encoding="utf-8")


@pytest.fixture
def matrix(html):
    return {b.fci_id: b for b in parse_breeds(html("matrix"), MATRIX_URL)}


@pytest.fixture
def catalogue():
    """Captured source data for offline API tests; see fixtures/README.md."""
    from fci_breeds.models import Snapshot

    return Snapshot.model_validate_json((FIXTURES / "catalogue.json").read_text(encoding="utf-8"))
