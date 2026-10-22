"""Parse FCI tables without flattening their CACIB award boundaries."""

import re
from datetime import datetime
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from .models import INDEX_URL, TRIAL_MEANINGS, Breed, Variety
from .normalize import typed_fields


class ParseError(ValueError):
    pass


def text(node: Tag | None) -> str:
    return " ".join(node.get_text(" ", strip=True).split()) if node else ""


def lines(node: Tag) -> list[str]:
    return [" ".join(s.split()) for s in node.get_text("\n", strip=True).splitlines() if s.strip()]


def soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def fci_url(href: str, base: str = INDEX_URL) -> str:
    url = urljoin(base, href)
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != "www.fci.be":
        raise ParseError(f"Unexpected source URL: {url}")
    return url


def date_value(value: str):
    if not value or value == "-":
        return None
    try:
        return datetime.strptime(value, "%m/%d/%Y").date()
    except ValueError as exc:
        raise ParseError(f"Invalid FCI date: {value}") from exc


def group_links(html: str) -> dict[int, str]:
    result = {}
    for a in soup(html).select(".grouplist .group a[href]"):
        match = re.fullmatch(r"Group (\d+)", text(a))
        if match:
            number = int(match[1])
            if number in result:
                raise ParseError(f"Duplicate group {number}")
            result[number] = fci_url(a["href"])
    if set(result) != set(range(1, 11)):
        raise ParseError(f"Expected all ten FCI groups, found {sorted(result)}")
    return result


def marker(row: Tag, cls: str, *, required: bool = True) -> str:
    cell = row.find("td", class_=cls, recursive=False)
    if cell is None and required:
        raise ParseError(f"Missing {cls} cell")
    value = text(cell)
    if value not in {"", "*", "(*)", "(**)"}:
        raise ParseError(f"Unknown {cls} marker: {value}")
    return value


def varieties(container: Tag, fci_id: int, inherited_group: str | None) -> list[Variety]:
    result = []
    consumed_subcells = 0
    cells = container.select("td.variete")
    for row_index, cell in enumerate(cells, 1):
        raw = lines(cell)
        if not raw:
            # Only the detail-table header may be blank; actual labels include "a)".
            if text(cell.parent.find("td", class_="varietecacib")) == "CACIB":
                continue
            raise ParseError(f"Missing variety label for {fci_id}")
        row = cell.parent
        award = marker(row, "varietecacib")
        award_id = f"{fci_id}:v{row_index}" if award else inherited_group
        parsed = []
        for label in raw:
            match = re.fullmatch(r"([a-z])\)\s*(.*)", label)
            if not match:
                raise ParseError(f"Unrecognized variety for {fci_id}: {label!r}")
            parsed.append((match[1], match[2]))
        children = []
        sibling = row.find_next_sibling("tr")
        if sibling and sibling.select_one(".sousvarietes"):
            for sub_index, subcell in enumerate(sibling.select("td.sousvariete"), 1):
                consumed_subcells += 1
                labels = lines(subcell)
                if not labels:
                    raise ParseError(f"Empty subvariety for {fci_id}")
                subaward = marker(subcell.parent, "sousvarietecacib")
                children.append(
                    Variety(
                        label=" / ".join(labels),
                        source_labels=labels,
                        cacib_marker=subaward,
                        cacib_group_id=f"{fci_id}:v{row_index}:s{sub_index}"
                        if subaward
                        else award_id,
                        **typed_fields(fci_id, labels),
                    )
                )
        for code, label in parsed:
            result.append(
                Variety(
                    code=code,
                    label=label,
                    source_labels=raw,
                    cacib_marker=award,
                    cacib_group_id=award_id,
                    subvarieties=[c.model_copy(deep=True) for c in children],
                    **typed_fields(fci_id, [label]),
                )
            )
    if len(container.select("td.sousvariete")) != consumed_subcells:
        raise ParseError(f"Orphan subvarieties for {fci_id}")
    codes = [v.code for v in result]
    if len(codes) != len(set(codes)):
        raise ParseError(f"Duplicate variety codes for {fci_id}")
    return result


def parse_breeds(
    html: str, url: str, *, provisional: bool = False, group: int | None = None
) -> list[Breed]:
    doc = soup(html)
    group_heading = text(doc.select_one(".nomenclature h2"))
    group_name = group_heading.split(" : ", 1)[-1] if group else None
    result = []
    consumed_variety_cells = 0
    for a in doc.select("td.race a.nom[href]"):
        match = re.fullmatch(r"(.+?)\s*\((\d+)\)(?:\s*\((.+)\))?", text(a))
        if not match:
            raise ParseError(f"Unrecognized breed: {text(a)}")
        breed_id = int(match[2])
        row = a.find_parent("tr")
        date_cell = row.find("td", class_="racedate", recursive=False)
        # Provisional index has recognition and validity dates, both class=racedate.
        dates = row.find_all("td", class_="racedate", recursive=False)
        if dates:
            date_cell = dates[-1]
        cacib = marker(row, "racecacib", required=not provisional)
        trial = marker(row, "raceepreuve", required=not provisional)
        section = country = None
        for parent in a.parents:
            if parent.name == "li" and parent.parent.name == "ul":
                classes = parent.parent.get("class", [])
                if "sections" in classes:
                    section = text(parent.find("span", recursive=False)) or None
                if "pays" in classes:
                    country = re.sub(r"^\d+\.\s*", "", text(parent.find("span", recursive=False)))
        breed = Breed(
            fci_id=breed_id,
            name=match[1].strip(),
            english_name=match[3],
            group=group,
            group_name=group_name,
            section=section,
            country=country,
            recognition_status="provisional" if provisional else "definitive",
            validity_date=date_value(text(date_cell)),
            source_url=fci_url(a["href"], url),
            varieties_source_url=url,
            cacib_marker=cacib,
            cacib_group_id=f"{breed_id}:breed" if cacib else None,
            working_trial_marker=trial,
            working_trial=TRIAL_MEANINGS[trial],
        )
        sibling = row.find_next_sibling("tr")
        if sibling and sibling.select_one("td.varietes"):
            consumed_variety_cells += len(sibling.select("td.variete"))
            breed.varieties = varieties(sibling, breed_id, breed.cacib_group_id)
        result.append(breed)
    if not result:
        raise ParseError(f"No breeds found at {url}")
    if len(result) != len(doc.select("td.race")):
        raise ParseError(f"Unparsed breed rows at {url}")
    if consumed_variety_cells != len(doc.select("td.variete")):
        raise ParseError(f"Unparsed variety tables at {url}")
    ids = [b.fci_id for b in result]
    if len(ids) != len(set(ids)):
        raise ParseError(f"Duplicate breed IDs at {url}")
    return result


def enrich_detail(breed: Breed, html: str) -> Breed:
    doc = soup(html)
    heading = text(doc.select_one(".nomenclature h2"))
    if not re.search(rf"\(\s*{breed.fci_id}\s*\)", heading):
        raise ParseError(f"Wrong detail page for {breed.fci_id}")

    def field(suffix):
        return text(doc.select_one(f'[id="ContentPlaceHolder1_{suffix}"]'))

    english = field("NomEnLabel")
    if not english:
        raise ParseError(f"Missing English name for {breed.fci_id}")
    breed.english_name = english
    group = field("GroupeHyperLink")
    match = re.fullmatch(r"n°(\d+)\s*-\s*(.+)", group)
    if not match:
        raise ParseError(f"Missing group for {breed.fci_id}")
    breed.group, breed.group_name = int(match[1]), match[2]
    breed.section = breed.section or field("SectionLabel") or None
    breed.country = breed.country or field("PaysOrigineLabel") or None
    breed.working_trial = field("EpreuveTravailLabel") or breed.working_trial
    if breed.recognition_status == "provisional":
        if "provisional" not in field("StatutLabel").lower():
            raise ParseError(f"Recognition status changed for {breed.fci_id}")
        breed.varieties = varieties(doc, breed.fci_id, None)
        breed.varieties_source_url = breed.source_url
    return breed
