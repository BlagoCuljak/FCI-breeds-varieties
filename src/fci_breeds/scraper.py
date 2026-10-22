import hashlib
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import httpx

from .models import INDEX_URL, MATRIX_URL, Snapshot
from .parser import ParseError, enrich_detail, fci_url, group_links, parse_breeds
from .validation import validate

LOG = logging.getLogger(__name__)
USER_AGENT = "FCIBreedsVarieties/0.1 (+https://github.com/BlagoCuljak/FCI-breeds-varieties)"


class Fetcher:
    def __init__(self, directory: Path, client: httpx.Client | None = None):
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=True)
        self.client = client or httpx.Client(
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
            limits=httpx.Limits(max_connections=3),
        )
        self.owns_client = client is None

    def close(self):
        if self.owns_client:
            self.client.close()

    def get(self, url: str) -> str:
        fci_url(url)
        key = hashlib.sha256(url.encode()).hexdigest()[:20]
        for attempt in range(3):
            try:
                time.sleep(0.3)
                response = self.client.get(url)
                if response.status_code == 429 or response.status_code >= 500:
                    response.raise_for_status()
                response.raise_for_status()
                fci_url(str(response.url))
                if "text/html" not in response.headers.get("content-type", ""):
                    raise ParseError(f"Expected HTML at {url}")
                html = response.text
                (self.directory / f"{key}.html").write_text(html, encoding="utf-8")
                (self.directory / f"{key}.json").write_text(json.dumps({"url": url}))
                LOG.info("Fetched %s", url)
                return html
            except httpx.HTTPError as exc:
                if isinstance(exc, httpx.HTTPStatusError):
                    status = exc.response.status_code
                    if status != 429 and status < 500:
                        raise
                if attempt == 2:
                    raise
                LOG.warning("Retry %s: %s", url, exc)
                time.sleep(2**attempt)
        raise AssertionError("Unreachable")


def scrape(directory: Path, previous: Snapshot | None = None) -> Snapshot:
    fetcher = Fetcher(directory)
    try:
        index = fetcher.get(INDEX_URL)
        links = group_links(index)
        provisional = parse_breeds(index, INDEX_URL, provisional=True)
        with ThreadPoolExecutor(max_workers=3) as pool:
            pages = list(pool.map(fetcher.get, links.values()))
            breeds = []
            for (group, url), html in zip(links.items(), pages, strict=True):
                breeds.extend(parse_breeds(html, url, group=group))
            breeds.extend(provisional)
            ids = [b.fci_id for b in breeds]
            if len(ids) != len(set(ids)):
                raise ParseError("A breed appears more than once in the catalogue")
            matrix = parse_breeds(fetcher.get(MATRIX_URL), MATRIX_URL)
            lookup = {b.fci_id: b for b in breeds}
            for entry in matrix:
                if entry.fci_id not in lookup:
                    raise ParseError(f"Matrix breed {entry.fci_id} is missing from catalogue")
                breed = lookup[entry.fci_id]
                if breed.recognition_status != "definitive":
                    raise ParseError(f"Provisional breed {entry.fci_id} appears in CACIB matrix")
                breed.varieties = entry.varieties
                breed.varieties_source_url = MATRIX_URL
                breed.cacib_marker = entry.cacib_marker
                breed.cacib_group_id = entry.cacib_group_id
                breed.working_trial_marker = entry.working_trial_marker
                breed.working_trial = entry.working_trial
                breed.validity_date = entry.validity_date
            needed = [
                b for b in breeds if not b.english_name or b.recognition_status == "provisional"
            ]
            LOG.info("Fetching %d detail pages for names and provisional metadata", len(needed))
            details = pool.map(fetcher.get, [b.source_url for b in needed])
            for breed, html in zip(needed, details, strict=True):
                enrich_detail(breed, html)
        snapshot = Snapshot(
            scraped_at=datetime.now(UTC),
            source_urls=sorted(
                {INDEX_URL, MATRIX_URL, *links.values(), *(b.source_url for b in needed)}
            ),
            breeds=sorted(breeds, key=lambda b: b.fci_id),
        )
        validate(snapshot, previous)
        return snapshot
    finally:
        fetcher.close()
