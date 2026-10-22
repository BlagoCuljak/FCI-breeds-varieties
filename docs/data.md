# Data format (v1)

`breeds.json` contains `schema_version`, `scraped_at` (UTC), `source_urls` and `breeds`. Individual endpoints contain the same version and timestamp plus `breed`. `/api/v1/schema.json` provides the complete JSON Schema. All endpoints describe the latest successful scrape.

Breeds contain the FCI ID, original and English names, FCI group and section, country label, recognition status, validity date, source URLs, working-trial marker and description, CACIB marker/group, and nested `varieties`. Names and dates come from the English FCI pages; original spelling and accents are preserved. Dates use ISO 8601. Group catalogue labels supply definitive breeds; detail pages fill missing names and provisional metadata. The varieties matrix takes precedence for listed breeds.

Each variety has a `code` (the source letter), `label`, `source_labels`, optional `size` and `coat`, `colors`, `cacib_marker`, `cacib_group_id` and `subvarieties`. A subvariety represents one source row, which may contain several colours sharing an award. Multiple lettered varieties in one row remain separate entries with the same source labels and CACIB group ID.

`cacib_group_id` links entries sharing an award, including awards inherited from a parent or breed. These are snapshot-local identifiers derived from table positions, **not official FCI codes or stable cross-version IDs**. An empty marker means the source cell is blank, not necessarily that CACIB is unavailable. Provisional breeds are not eligible for CACIB. Working-trial markers retain the FCI distinctions: `*` applies normally, `(*)` only in countries that requested it, and `(**)` only in Finland, Norway and Sweden.

Typed fields use conservative, explicit mappings. Unclassified values stay in source labels; nulls and empty arrays mean no reliable classification. The current mappings recognize Poodle/Dachshund sizes, common coat labels and exact colour labels. They do not infer colours from breed names. Blank source varieties such as `a)` remain present with an empty label.

The CSV contains one row per leaf variety/group, or one row for a breed with no varieties. It repeats breed metadata, preserves the parent variety and leaf labels, and includes both parent and effective CACIB groups. Array-valued cells (`colors`, `variety_source_labels`, `subvariety_source_labels`) are JSON arrays. CSV quoting follows Python's standard CSV writer and preserves Unicode. A multi-colour CACIB group stays together in one row.

`meta.json` includes counts, scrape time and the SHA-256 checksum of the exact UTF-8 bytes of `breeds.json`. Check its timestamp for freshness; a successful HTTP response does not imply a recent scrape. Consumers should refresh the catalogue as a whole when they need a consistent snapshot across deployment boundaries.

Publication requires all ten groups, provisional coverage, at least 300 breeds, unique IDs, complete required metadata and intact reference varieties. Comparing against `--previous` also rejects losses greater than 5% of breeds/varieties/leaves or 2% of known breed IDs. Legitimate major source changes require reviewing and updating these guards before publication.
