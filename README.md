# FCI breeds & varieties

The official FCI breed catalogue, including provisional breeds, nested varieties and CACIB groups. Scraped nightly with Python and served as a static JSON API and CSV on Cloudflare.

Powered by the <a href="https://dogshowonline.com/"><img src="https://dogshowonline.com/img/dogshowonline-logo.svg" alt="" height="24" align="center"> DogShowOnline.com</a> platform.

## Run locally

```sh
uv sync --locked
uv run fci-breeds scrape --output artifacts/snapshot.json
uv run fci-breeds validate artifacts/snapshot.json
uv run fci-breeds export artifacts/snapshot.json --output dist
npm ci
npm run dev
```

## API

Fetch data from **[https://fci.dogshowonline.com](https://fci.dogshowonline.com)** using these endpoints:

| URL | Returns |
| --- | --- |
| [https://fci.dogshowonline.com/api/v1/breeds.json](https://fci.dogshowonline.com/api/v1/breeds.json) | Complete nested catalogue |
| [https://fci.dogshowonline.com/api/v1/breeds/172.json](https://fci.dogshowonline.com/api/v1/breeds/172.json) | One breed by FCI ID; replace `172` with the desired ID |
| [https://fci.dogshowonline.com/api/v1/breeds.csv](https://fci.dogshowonline.com/api/v1/breeds.csv) | Complete CSV download |
| [https://fci.dogshowonline.com/api/v1/meta.json](https://fci.dogshowonline.com/api/v1/meta.json) | Scrape time, counts and checksum |

```sh
curl https://fci.dogshowonline.com/api/v1/breeds.json
curl -o fci-breeds-varieties.csv https://fci.dogshowonline.com/api/v1/breeds.csv
```

Public access, UTF-8 and CORS. Filter the JSON in your application and check `meta.json` for freshness. See [data format](docs/data.md) for fields and CSV conventions.

## Tests

```sh
uv run ruff check .
uv run pytest
uv run playwright install chromium
uv run python scripts/explore.py  # live source inspection and screenshots
```

Data source: [Fédération Cynologique Internationale](https://www.fci.be/en/nomenclature/) and its [varieties matrix](https://www.fci.be/en/nomenclature/varietes.aspx). This project is independent of FCI. The MIT license covers the code; source data remains attributed to FCI.
