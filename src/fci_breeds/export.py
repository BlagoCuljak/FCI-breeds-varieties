import csv
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

from .models import Breed, Snapshot
from .validation import counts, validate

CSV_FIELDS = [
    "fci_id",
    "name",
    "english_name",
    "group",
    "group_name",
    "section",
    "country",
    "recognition_status",
    "validity_date",
    "source_url",
    "varieties_source_url",
    "working_trial_marker",
    "working_trial",
    "breed_cacib_marker",
    "breed_cacib_group_id",
    "variety_code",
    "variety_label",
    "variety_source_labels",
    "variety_cacib_marker",
    "variety_cacib_group_id",
    "subvariety_label",
    "subvariety_source_labels",
    "size",
    "coat",
    "colors",
    "cacib_marker",
    "cacib_group_id",
]


def json_text(value) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def rows(breed: Breed):
    data = breed.model_dump(mode="json")
    base = {key: data[key] for key in CSV_FIELDS if key in data and key != "varieties"}
    base["breed_cacib_marker"] = breed.cacib_marker
    base["breed_cacib_group_id"] = breed.cacib_group_id
    if not breed.varieties:
        yield {
            **base,
            "colors": "[]",
            "variety_source_labels": "[]",
            "subvariety_source_labels": "[]",
        }
    for variety in breed.varieties:
        for leaf in variety.subvarieties or [variety]:
            sub = leaf is not variety
            yield {
                **base,
                "variety_code": variety.code,
                "variety_label": variety.label,
                "variety_source_labels": json.dumps(variety.source_labels, ensure_ascii=False),
                "variety_cacib_marker": variety.cacib_marker,
                "variety_cacib_group_id": variety.cacib_group_id,
                "subvariety_label": leaf.label if sub else "",
                "subvariety_source_labels": json.dumps(
                    leaf.source_labels if sub else [], ensure_ascii=False
                ),
                "size": leaf.size or variety.size,
                "coat": leaf.coat or variety.coat,
                "colors": json.dumps(leaf.colors or variety.colors, ensure_ascii=False),
                "cacib_marker": leaf.cacib_marker,
                "cacib_group_id": leaf.cacib_group_id,
            }


def export(snapshot: Snapshot, destination: Path):
    validate(snapshot)
    destination = destination.resolve()
    if destination.exists() and not (destination / "api/v1/meta.json").is_file():
        raise ValueError(f"Refusing to replace non-export directory: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".fci-export-", dir=destination.parent))
    try:
        api = staging / "api/v1"
        (api / "breeds").mkdir(parents=True)
        payload = snapshot.model_dump(mode="json")
        # Publish the complete snapshot so consumers can identify its timestamp and schema.
        catalogue = json_text(payload)
        (api / "breeds.json").write_text(catalogue, encoding="utf-8")
        for breed in snapshot.breeds:
            (api / f"breeds/{breed.fci_id}.json").write_text(
                json_text(
                    {
                        "schema_version": snapshot.schema_version,
                        "scraped_at": payload["scraped_at"],
                        "breed": breed.model_dump(mode="json"),
                    }
                ),
                encoding="utf-8",
            )
        with (api / "breeds.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
            writer.writeheader()
            for breed in snapshot.breeds:
                writer.writerows(rows(breed))
        metadata = {
            "schema_version": snapshot.schema_version,
            "scraped_at": payload["scraped_at"],
            "source_urls": snapshot.source_urls,
            "counts": counts(snapshot),
            "sha256": hashlib.sha256(catalogue.encode("utf-8")).hexdigest(),
            "checksum_file": "/api/v1/breeds.json",
            "powered_by": {"name": "DogShowOnline.com", "url": "https://dogshowonline.com/"},
        }
        (api / "meta.json").write_text(json_text(metadata), encoding="utf-8")
        (api / "schema.json").write_text(json_text(Snapshot.model_json_schema()), encoding="utf-8")
        (staging / "_headers").write_text(
            "/api/*\n  Access-Control-Allow-Origin: *\n"
            "  Cache-Control: public, max-age=0, must-revalidate\n"
            "  X-Content-Type-Options: nosniff\n"
            "/api/v1/breeds.csv\n"
            '  Content-Disposition: attachment; filename="fci-breeds-varieties.csv"\n'
            "  Content-Type: text/csv; charset=utf-8\n",
            encoding="utf-8",
        )
        (staging / "404.html").write_text("<!doctype html><title>Not found</title>Not found\n")
        if destination.exists():
            shutil.rmtree(destination)
        staging.rename(destination)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
