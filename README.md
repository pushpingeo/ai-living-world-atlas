# AI Living World Atlas

An open index of the world's public map services, built to be read by AI agents first.

Government bodies publish huge numbers of map layers through ArcGIS REST and OGC services (WMS, WFS), but they are hard to find and nobody tells you when one breaks. This project crawls the public ones, keeps the publisher's own metadata, scores each layer for how far you can trust it, and checks that it still returns data.

**Status:** early. A UK test crawl comes first, to find out how much good metadata is really out there before going global.

## How it works

1. **Seeds.** Catalogues come from the [Dateno data portals registry](https://github.com/commondataio/dataportals-registry) (CC BY 4.0): ArcGIS servers, GeoServers, ArcGIS Hub sites and CKAN portals, each with an owner type.
2. **Catalogues first.** Hub and CKAN records point to the services a public body stands behind. They also tend to have the best descriptions and licence text.
3. **Services.** Each service is crawled once to list all its layers, so re-checking the whole index is cheap.
4. **Checks.** A tiny request per layer confirms it still returns features or an image.
5. **Trust score.** Four visible parts: who publishes it, how complete the metadata is, whether it works, and how clear the licence is.
6. **Output.** One row per layer in GeoParquet, which DuckDB can query straight from a URL.

The index links to data; it doesn't copy it. Publisher text is stored exactly as published. Anything we add (AI summaries, theme tags) goes in separate, labelled fields.

## Running a crawl

```bash
pip install -r requirements.txt
curl -sSfL -o registry.parquet https://raw.githubusercontent.com/commondataio/dataportals-registry/main/data/datasets/full.parquet
python -m atlas.spike --registry registry.parquet --countries GB --out out/gb --minutes 30
```

In GitHub Actions, edit a file in `runs/` and push. Results land on a `results/...` branch.

## Layout

- `atlas/`: crawler, quality scoring and report
- `vocab/themes.yaml`: ISO 19115 topic categories, with crosswalks from INSPIRE and data.gov.uk themes
- `docs/decisions.md`: design decisions and why

## Crawling politely

One user agent that names this project, at most two requests at a time to any host, and robots.txt is respected. If you run a service and want it left out, open an issue.
