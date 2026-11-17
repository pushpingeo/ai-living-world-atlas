# Spike report: EMODNET

Run time 5.8 min; 482 HTTP requests; 96 blocked by robots.txt.

## Coverage
- Catalogues harvested: 2/2 (records linking to services: 4268)
- ArcGIS server roots reachable: 0/0
- Services crawled OK: 162/272 (skipped for time: 0); by type {'wfs': 26, 'wms': 132, 'wcs': 4}
- **Layers found: 7395** ({'wms': 6789, 'wfs': 339, 'wcs': 267})
- Distinct title+publisher (rough dedupe): 2436

## Metadata quality
- Abstract of 50+ chars: 64%
- Any licence/constraints text: 86%; recognised open licence: 8%
- Keywords: 23%; WGS84 extent: 100%
- Linked to a catalogue record: 11%
- Code-like layer titles (before using catalogue names): 1%; junk-flagged: 0%
- **Declares an ISO theme (directly or via INSPIRE/DGU crosswalk): 10%** {'none': 6661, 'theme-field': 672, 'keyword': 62}
- Publisher type: {'international': 7395}

## Datasets (endpoints grouped)
- **Datasets: 4221** from 7395 endpoints; passing: 2529
- Reachable by more than one protocol: 309
- Endpoints per dataset: {1: 2793, 2: 730, 3: 262, 4: 184, 5: 52, 6: 116, 7: 8, 8: 76}
- Grouping rules used: {'title-extent': 1053, 'ogc-name': 284, 'catalogue': 102}
- Role (all / passing): {'data': 4213, 'imagery': 6, 'basemap': 2} / {'data': 2521, 'imagery': 6, 'basemap': 2}
- Capabilities offered: {'render': 3935, 'feature-info': 3864, 'time': 2332, 'download': 595, 'query': 328, 'pixels': 267}

## Coverage and detail
- Coverage level (from extent): {'continental': 3259, 'regional': 1403, 'global': 1348, 'national': 1128, 'local': 252, 'unknown': 5}
- Extent source: {'declared': 7395}; suspect-extent flags: {'world': 278, 'shared-default': 107, 'grid-default': 4}
- Endpoints that allow browser access (CORS): 7390
- Detail estimate source: {'none': 6911, 'metadata': 357, 'stated': 109, 'display': 18}
- Detail level, all layers: {'unknown': 6911, '1:100k': 230, '1:2M': 117, '1:500k': 93, 'coarser': 23, '1:25k': 20, '1:5k': 1}
- Detail level, passing layers: {'unknown': 4274, '1:100k': 230, '1:2M': 117, '1:500k': 92, 'coarser': 23, '1:25k': 20, '1:5k': 1}

## Liveness (sample, up to 2 layers per service)
- {'unchecked': 7283, 'ok': 108, 'fail': 4}
- Returns data: 0.964; returns data or valid empty: 0.964

## Quality bar
- **Pass: 4757 layers (64%)**; distinct among passing: 1638
- Score median 78.0; bands {'[50, 60)': 21, '[60, 70)': 446, '[70, 80)': 5097, '[80, 101)': 1831}

## Size
- layers.parquet: 0.67 MB for 7395 layers

## Top service errors
- robots.txt disallows: 88
- HTTP N: 15
- TimeoutError: : 5
- ClientConnectorError: Cannot connect to host localhost:N : 1
- ClientConnectorCertificateError: Cannot connect to host www.: 1

AI-tag agreement is not in this run (needs the API key); it comes next.
