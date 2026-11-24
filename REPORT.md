# Spike report: UKPACK

Run time 0.2 min; 63 HTTP requests; 3 blocked by robots.txt.

## Coverage
- Catalogues harvested: 0/0 (records linking to services: 0)
- ArcGIS server roots reachable: 0/0
- Services crawled OK: 0/0 (skipped for time: 0); by type {}
- **Layers found: 90** ({'landing': 45, 'arcgis-featureserver': 26, 'wfs': 10, 'arcgis-mapserver': 9})
- Distinct title+publisher (rough dedupe): 45

## Metadata quality
- Abstract of 50+ chars: 100%
- Any licence/constraints text: 100%; recognised open licence: 96%
- Keywords: 100%; WGS84 extent: 100%
- Linked to a catalogue record: 0%
- Code-like layer titles (before using catalogue names): 0%; junk-flagged: 0%
- **Declares an ISO theme (directly or via INSPIRE/DGU crosswalk): 11%** {'none': 80, 'keyword': 10}
- Publisher type: {'public-body': 90}

## Datasets (endpoints grouped)
- **Datasets: 45** from 90 endpoints; passing: 45
- Reachable by more than one protocol: 45
- Endpoints per dataset: {2: 45}
- Grouping rules used: {'catalogue': 40, 'arcgis-ogc': 5}
- Role (all / passing): {'data': 45} / {'data': 45}
- Capabilities offered: {'query': 45, 'download': 29}

## Coverage and detail
- Coverage level (from extent): {'national': 50, 'regional': 38, 'local': 2}
- Extent source: {'curated': 90}; suspect-extent flags: {}
- Endpoints that allow browser access (CORS): 0
- Detail estimate source: {'none': 84, 'stated': 6}
- Detail level, all layers: {'unknown': 84, '1:500k': 6}
- Detail level, passing layers: {'unknown': 84, '1:500k': 6}

## Liveness (sample, up to 2 layers per service)
- {'ok': 63, 'unchecked': 27}
- Returns data: 1.0; returns data or valid empty: 1.0

## Quality bar
- **Pass: 90 layers (100%)**; distinct among passing: 45
- Score median 95.0; bands {'[80, 101)': 90}

## Size
- layers.parquet: 0.07 MB for 90 layers

## Top service errors

AI-tag agreement is not in this run (needs the API key); it comes next.
