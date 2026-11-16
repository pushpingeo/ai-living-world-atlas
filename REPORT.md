# Spike report: GLOBAL

Run time 96.7 min; 36990 HTTP requests; 402 blocked by robots.txt.

## Coverage
- Catalogues harvested: 1/1 (records linking to services: 6254)
- ArcGIS server roots reachable: 56/73
- Services crawled OK: 11984/13638 (skipped for time: 0); by type {'arcgis-imageserver': 1323, 'arcgis-vectortileserver': 105, 'arcgis-mapserver': 4741, 'arcgis-featureserver': 5804, 'wms': 9, 'wmts': 1, 'wfs': 1}
- **Layers found: 61719** ({'arcgis-mapserver': 44517, 'arcgis-featureserver': 12169, 'wms': 2277, 'wmts': 1330, 'arcgis-imageserver': 1255, 'arcgis-vectortileserver': 105, 'wfs': 54, 'landing': 4, 'cloud': 3, 'api': 3, 'download': 2})
- Distinct title+publisher (rough dedupe): 33190

## Metadata quality
- Abstract of 50+ chars: 24%
- Any licence/constraints text: 70%; recognised open licence: 2%
- Keywords: 66%; WGS84 extent: 99%
- Linked to a catalogue record: 9%
- Code-like layer titles (before using catalogue names): 28%; junk-flagged: 0%
- **Declares an ISO theme (directly or via INSPIRE/DGU crosswalk): 24%** {'none': 47145, 'keyword': 14574}
- Publisher type: {'curated-collection': 44506, 'international': 15712, 'public-body': 1501}

## Datasets (endpoints grouped)
- **Datasets: 46483** from 61719 endpoints; passing: 11443
- Reachable by more than one protocol: 3121
- Endpoints per dataset: {1: 38436, 2: 5910, 3: 257, 4: 733, 5: 100, 6: 537, 7: 42, 8: 468}
- Grouping rules used: {'title-extent': 5201, 'arcgis-pair': 2925, 'ogc-name': 54, 'catalogue': 1}
- Role (all / passing): {'data': 44608, 'imagery': 1703, 'elevation': 161, 'basemap': 11} / {'data': 11301, 'elevation': 106, 'imagery': 32, 'basemap': 4}
- Capabilities offered: {'render': 36779, 'query': 25091, 'tiles': 13066, 'time': 4859, 'download': 3879, 'feature-info': 2188, 'catalog': 658, 'raster-functions': 382, 'multidimensional': 97, 'pixels': 16, 'cloud': 3}

## Coverage and detail
- Coverage level (from extent): {'national': 25573, 'global': 13898, 'local': 9948, 'regional': 7148, 'continental': 4493, 'unknown': 659}
- Extent source: {'declared': 56180, 'measured': 5539}; suspect-extent flags: {'world': 6210, 'shared-default': 5107, 'grid-default': 210}
- Endpoints that allow browser access (CORS): 61707
- Detail estimate source: {'none': 50200, 'stated': 5247, 'display': 3237, 'tile-cache': 1779, 'pixel-size': 1256}
- Detail level, all layers: {'unknown': 50200, '1:500k': 2807, '1:100k': 2229, 'coarser': 2224, '1:25k': 2165, '1:2M': 1316, '1:5k': 778}
- Detail level, passing layers: {'unknown': 9705, '1:500k': 1029, '1:2M': 630, '1:100k': 481, '1:5k': 247, '1:25k': 239, 'coarser': 225}

## Liveness (sample, up to 2 layers per service)
- {'unchecked': 56991, 'ok': 4641, 'fail': 64, 'empty': 23}
- Returns data: 0.982; returns data or valid empty: 0.986

## Quality bar
- **Pass: 12556 layers (20%)**; distinct among passing: 10445
- Score median 72.0; bands {'[40, 50)': 4258, '[50, 60)': 12217, '[60, 70)': 8065, '[70, 80)': 28204, '[80, 101)': 8975}

## Size
- layers.parquet: 14.64 MB for 61719 layers

## Top service errors
- {'code': N, 'details': 'error', 'message': 'HTTP N Not F: 908
- robots.txt disallows: 390
- {'code': N, 'details': [], 'message': 'Service not found'}: 149
- TimeoutError: : 67
- {'code': N, 'message': 'Error handling service request :Il: 66
- {'code': N, 'details': [], 'message': 'Service not found.': 28
- {'code': N, 'message': 'Error handling service request :0x: 14
- HTTP N: 7

AI-tag agreement is not in this run (needs the API key); it comes next.
