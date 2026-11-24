# Spike report: FILL

Run time 8.3 min; 3458 HTTP requests; 1 blocked by robots.txt.

## Coverage
- Catalogues harvested: 3/3 (records linking to services: 557)
- ArcGIS server roots reachable: 8/14
- Services crawled OK: 473/1279 (skipped for time: 0); by type {'arcgis-imageserver': 103, 'wms': 14, 'arcgis-mapserver': 153, 'wmts': 1, 'arcgis-featureserver': 201, 'wfs': 1}
- **Layers found: 6903** ({'arcgis-mapserver': 2809, 'wms': 1932, 'wmts': 1332, 'wfs': 399, 'arcgis-featureserver': 323, 'arcgis-imageserver': 103, 'download': 4, 'landing': 1})
- Distinct title+publisher (rough dedupe): 4854

## Metadata quality
- Abstract of 50+ chars: 25%
- Any licence/constraints text: 84%; recognised open licence: 2%
- Keywords: 44%; WGS84 extent: 94%
- Linked to a catalogue record: 5%
- Code-like layer titles (before using catalogue names): 41%; junk-flagged: 0%
- **Declares an ISO theme (directly or via INSPIRE/DGU crosswalk): 3%** {'none': 6693, 'keyword': 210}
- Publisher type: {'central-gov': 5811, 'research': 660, 'civil-society': 223, 'public-body': 149, 'international': 60}

## Datasets (endpoints grouped)
- **Datasets: 5100** from 6903 endpoints; passing: 463
- Reachable by more than one protocol: 76
- Endpoints per dataset: {1: 4631, 2: 216, 3: 1, 4: 21, 5: 25, 6: 10, 8: 196}
- Grouping rules used: {'title-extent': 445, 'arcgis-pair': 18, 'ogc-name': 6}
- Role (all / passing): {'imagery': 2946, 'data': 2151, 'elevation': 3} / {'data': 404, 'imagery': 57, 'elevation': 2}
- Capabilities offered: {'render': 3149, 'tiles': 1731, 'query': 1570, 'time': 1191, 'download': 555, 'feature-info': 309, 'catalog': 77, 'raster-functions': 56, 'multidimensional': 30, 'pixels': 11}

## Coverage and detail
- Coverage level (from extent): {'global': 4497, 'continental': 970, 'national': 721, 'unknown': 393, 'regional': 237, 'local': 85}
- Extent source: {'declared': 5897, 'measured': 1001, 'curated': 5}; suspect-extent flags: {'world': 4168, 'shared-default': 3488, 'grid-default': 92}
- Endpoints that allow browser access (CORS): 6493
- Detail estimate source: {'none': 4505, 'tile-cache': 1327, 'stated': 912, 'pixel-size': 106, 'display': 53}
- Detail level, all layers: {'unknown': 4505, 'coarser': 1953, '1:2M': 240, '1:25k': 78, '1:100k': 59, '1:500k': 56, '1:5k': 12}
- Detail level, passing layers: {'unknown': 310, '1:25k': 62, 'coarser': 45, '1:100k': 28, '1:2M': 22, '1:500k': 20, '1:5k': 8}

## Liveness (sample, up to 2 layers per service)
- {'unchecked': 6311, 'ok': 557, 'fail': 26, 'empty': 9}
- Returns data: 0.941; returns data or valid empty: 0.956

## Quality bar
- **Pass: 495 layers (7%)**; distinct among passing: 448
- Score median 73.0; bands {'[0, 40)': 654, '[40, 50)': 157, '[50, 60)': 169, '[60, 70)': 1408, '[70, 80)': 2791, '[80, 101)': 1724}

## Size
- layers.parquet: 0.77 MB for 6903 layers

## Top service errors
- {'code': N, 'details': 'error', 'message': 'HTTP N Not F: 505
- HTTP N: 195
- {'code': N, 'details': [], 'message': 'Service not found'}: 69
- {'code': N, 'details': [], 'message': 'Service not found.': 28
- {'code': N, 'details': [], 'message': 'Token Required'}: 3
- TimeoutError: : 2
- parse: ParseError: no element found: line 1, column N: 1
- {'code': N, 'message': 'Invalid URL', 'details': ['Invalid: 1

AI-tag agreement is not in this run (needs the API key); it comes next.
