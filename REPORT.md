# Spike report: VALUES

Run time 0.9 min; 19 HTTP requests; 8 blocked by robots.txt.

## Coverage
- Catalogues harvested: 0/0 (records linking to services: 0)
- ArcGIS server roots reachable: 0/0
- Services crawled OK: 0/0 (skipped for time: 0); by type {}
- **Layers found: 47** ({'api': 24, 'arcgis-imageserver': 9, 'landing': 6, 'wcs': 4, 'cloud': 2, 'opendap': 1, 'download': 1})
- Distinct title+publisher (rough dedupe): 40

## Metadata quality
- Abstract of 50+ chars: 100%
- Any licence/constraints text: 98%; recognised open licence: 91%
- Keywords: 100%; WGS84 extent: 100%
- Linked to a catalogue record: 0%
- Code-like layer titles (before using catalogue names): 0%; junk-flagged: 0%
- **Declares an ISO theme (directly or via INSPIRE/DGU crosswalk): 72%** {'keyword': 34, 'none': 13}
- Publisher type: {'central-gov': 29, 'international': 15, 'academic': 2, 'regional-gov': 1}

## Datasets (endpoints grouped)
- **Datasets: 40** from 47 endpoints; passing: 40
- Reachable by more than one protocol: 7
- Endpoints per dataset: {1: 33, 2: 7}
- Grouping rules used: {'catalogue': 7}
- Role (all / passing): {'elevation': 31, 'data': 9} / {'elevation': 31, 'data': 9}
- Capabilities offered: {'sample': 40, 'render': 9, 'download': 7, 'tiles': 6, 'pixels': 4, 'cloud': 2, 'catalog': 1, 'raster-functions': 1}

## Coverage and detail
- Coverage level (from extent): {'global': 20, 'national': 11, 'regional': 11, 'continental': 3, 'local': 2}
- Extent source: {'curated': 47}; suspect-extent flags: {}
- Endpoints that allow browser access (CORS): 0
- Detail estimate source: {'pixel-size': 28, 'none': 19}
- Detail level, all layers: {'unknown': 19, '1:2M': 16, '1:5k': 8, '1:100k': 2, '1:25k': 2}
- Detail level, passing layers: {'unknown': 19, '1:2M': 14, '1:5k': 8, '1:100k': 2, '1:25k': 2}

## Liveness (sample, up to 2 layers per service)
- {'unchecked': 30, 'ok': 15, 'fail': 2}
- Returns data: 0.882; returns data or valid empty: 0.882

## Quality bar
- **Pass: 45 layers (96%)**; distinct among passing: 40
- Score median 95.0; bands {'[80, 101)': 47}

## Size
- layers.parquet: 0.07 MB for 47 layers

## Top service errors

AI-tag agreement is not in this run (needs the API key); it comes next.
