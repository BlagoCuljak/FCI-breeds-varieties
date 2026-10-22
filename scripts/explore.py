"""Read-only Playwright inspection of the source; artifacts stay outside version control."""

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

from fci_breeds.models import INDEX_URL, MATRIX_URL
from fci_breeds.parser import group_links, parse_breeds

out = Path("artifacts/exploration")
out.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    page.goto(INDEX_URL, wait_until="domcontentloaded")
    links = group_links(page.content())
    provisional = parse_breeds(page.content(), INDEX_URL, provisional=True)
    page.goto(MATRIX_URL, wait_until="domcontentloaded")
    page.locator("td.race a.nom").first.wait_for()
    html = page.content()
    matrix = parse_breeds(html, MATRIX_URL)
    lookup = {b.fci_id: b for b in matrix}
    assert len(lookup[172].varieties) == 4
    assert sum(len(v.subvarieties) for v in lookup[148].varieties) == 9
    assert len(lookup[15].varieties) == 4
    assert len(lookup[218].varieties) == 2
    (out / "matrix.html").write_text(html, encoding="utf-8")
    page.screenshot(path=str(out / "matrix.png"), full_page=True)
    report = {
        "groups": len(links),
        "matrix_breeds": len(matrix),
        "provisional_breeds": len(provisional),
        "poodle": lookup[172].model_dump(mode="json"),
    }
    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k != "poodle"}))
    browser.close()
