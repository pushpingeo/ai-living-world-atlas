# Spike report: UKGROUND

Run time 0.1 min; 33 HTTP requests; 0 blocked by robots.txt.

## Coverage
- Catalogues harvested: 0/0 (records linking to services: 0)
- ArcGIS server roots reachable: 0/0
- Services crawled OK: 0/0 (skipped for time: 0); by type {}
- **Layers found: 34** ({'landing': 16, 'arcgis-featureserver': 10, 'wfs': 5, 'arcgis-mapserver': 3})
- Distinct title+publisher (rough dedupe): 16

## Metadata quality
- Abstract of 50+ chars: 100%
- Any licence/constraints text: 100%; recognised open licence: 41%
- Keywords: 100%; WGS84 extent: 100%
- Linked to a catalogue record: 0%
- Code-like layer titles (before using catalogue names): 0%; junk-flagged: 0%
- **Declares an ISO theme (directly or via INSPIRE/DGU crosswalk): 0%** {'none': 34}
- Publisher type: {'public-body': 22, 'local-gov': 12}

## Datasets (endpoints grouped)
- **Datasets: 16** from 34 endpoints; passing: 16
- Reachable by more than one protocol: 16
- Endpoints per dataset: {2: 15, 4: 1}
- Grouping rules used: {'catalogue': 13, 'arcgis-ogc': 3}
- Role (all / passing): {'data': 16} / {'data': 16}
- Capabilities offered: {'query': 16, 'download': 3}

## Coverage and detail
- Coverage level (from extent): {'national': 14, 'local': 12, 'regional': 8}
- Extent source: {'curated': 34}; suspect-extent flags: {}
- Endpoints that allow browser access (CORS): 0
- Detail estimate source: {'none': 32, 'stated': 2}
- Detail level, all layers: {'unknown': 32, '1:2M': 2}
- Detail level, passing layers: {'unknown': 32, '1:2M': 2}

## Liveness (sample, up to 2 layers per service)
- {'ok': 33, 'unchecked': 1}
- Returns data: 1.0; returns data or valid empty: 1.0

## Quality bar
- **Pass: 34 layers (100%)**; distinct among passing: 16
- Score median 92.0; bands {'[80, 101)': 34}

## Size
- layers.parquet: 0.07 MB for 34 layers

## Top service errors

AI-tag agreement is not in this run (needs the API key); it comes next.
