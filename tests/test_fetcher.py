import httpx
import pytest

from fci_breeds.models import INDEX_URL
from fci_breeds.parser import ParseError
from fci_breeds.scraper import Fetcher


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr("fci_breeds.scraper.time.sleep", lambda _: None)


def test_retry_then_save(tmp_path):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(
            503 if len(calls) < 3 else 200,
            headers={"content-type": "text/html"},
            text="<html>OK</html>",
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        assert Fetcher(tmp_path, client).get(INDEX_URL) == "<html>OK</html>"
    assert len(calls) == 3
    assert len(list(tmp_path.glob("*.html"))) == 1


def test_timeout_never_returns_partial_result(tmp_path):
    calls = []

    def handler(request):
        calls.append(request)
        raise httpx.ReadTimeout("Source timeout", request=request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(httpx.ReadTimeout):
            Fetcher(tmp_path, client).get(INDEX_URL)
    assert len(calls) == 3
    assert not list(tmp_path.glob("*.html"))


def test_reject_non_html(tmp_path):
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(200, headers={"content-type": "application/json"}, text="{}")
        )
    ) as client:
        with pytest.raises(ParseError, match="Expected HTML"):
            Fetcher(tmp_path, client).get(INDEX_URL)
