import argparse
import json
import logging
from pathlib import Path

from .export import export
from .models import Snapshot
from .scraper import scrape
from .validation import counts, validate


def load(path: Path) -> Snapshot:
    return Snapshot.model_validate_json(path.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description="Scrape and publish the official FCI catalogue")
    commands = parser.add_subparsers(dest="command", required=True)
    collect = commands.add_parser("scrape", help="Fetch and validate a complete snapshot")
    collect.add_argument("--output", type=Path, default=Path("artifacts/snapshot.json"))
    collect.add_argument("--raw-dir", type=Path, default=Path("artifacts/raw"))
    collect.add_argument("--previous", type=Path)
    check = commands.add_parser("validate", help="Validate a saved snapshot")
    check.add_argument("snapshot", type=Path)
    check.add_argument("--previous", type=Path)
    publish = commands.add_parser("export", help="Generate the static API and CSV")
    publish.add_argument("snapshot", type=Path)
    publish.add_argument("--output", type=Path, default=Path("dist"))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        if args.command == "scrape":
            snapshot = scrape(args.raw_dir, load(args.previous) if args.previous else None)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            temp = args.output.with_suffix(".tmp")
            temp.write_text(snapshot.model_dump_json(indent=2) + "\n", encoding="utf-8")
            temp.replace(args.output)
        else:
            snapshot = load(args.snapshot)
            if args.command == "validate":
                validate(snapshot, load(args.previous) if args.previous else None)
            else:
                export(snapshot, args.output)
        print(json.dumps(counts(snapshot), sort_keys=True))
    except Exception as exc:
        logging.error("%s", exc)
        raise SystemExit(1) from exc
