"""Check a local Wrangler server or the published static API."""

import argparse
import csv
import hashlib
import io
import json
import time
from pathlib import Path

import httpx

parser = argparse.ArgumentParser()
parser.add_argument("base_url")
parser.add_argument("--expected-meta", type=Path)
args = parser.parse_args()
base = args.base_url.rstrip("/")
expected = json.loads(args.expected_meta.read_text()) if args.expected_meta else None
with httpx.Client(base_url=base, timeout=30) as client:
    for attempt in range(30):
        try:
            meta_response = client.get("/api/v1/meta.json")
            meta_response.raise_for_status()
            if expected:
                assert meta_response.json()["sha256"] == expected["sha256"], (
                    "Published snapshot does not match the build"
                )
            break
        except (httpx.HTTPError, AssertionError):
            if attempt == 29:
                raise
            time.sleep(1)
    meta = meta_response.json()
    response = client.get("/api/v1/breeds.json")
    response.raise_for_status()
    assert "application/json" in response.headers["content-type"]
    assert response.headers["access-control-allow-origin"] == "*"
    assert hashlib.sha256(response.content).hexdigest() == meta["sha256"]
    snapshot = response.json()
    assert snapshot["scraped_at"] == meta["scraped_at"]
    assert len(snapshot["breeds"]) == meta["counts"]["breeds"]
    detail = client.get("/api/v1/breeds/172.json")
    detail.raise_for_status()
    assert detail.json()["breed"]["fci_id"] == 172
    assert len(detail.json()["breed"]["varieties"]) == 4
    download = client.get("/api/v1/breeds.csv")
    download.raise_for_status()
    assert "attachment" in download.headers["content-disposition"]
    assert "text/csv" in download.headers["content-type"]
    rows = list(csv.DictReader(io.StringIO(download.text)))
    assert len(rows) == meta["counts"]["leaves"]
    assert {int(r["fci_id"]) for r in rows} == {b["fci_id"] for b in snapshot["breeds"]}
    assert client.get("/api/v1/breeds/999999.json").status_code == 404
    assert client.get("/unknown-path").status_code == 404
    print(f"Passed: {len(snapshot['breeds'])} breeds, {len(rows)} CSV rows at {base}")
