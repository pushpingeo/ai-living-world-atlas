# Spike report: GB

Run time 107.0 min; 37962 HTTP requests; 608 blocked by robots.txt.

## Coverage
- Catalogues harvested: 85/142 (records linking to services: 18899)
- ArcGIS server roots reachable: 42/91
- Services crawled OK: 13880/17425 (skipped for time: 0); by type {'arcgis-imageserver': 234, 'wfs': 1217, 'wms': 1102, 'arcgis-mapserver': 4263, 'arcgis-featureserver': 6955, 'arcgis-vectortileserver': 40, 'wcs': 47, 'wmts': 22}
- **Layers found: 61520** ({'arcgis-mapserver': 25496, 'wms': 14557, 'wfs': 10690, 'arcgis-featureserver': 8703, 'wmts': 1177, 'wcs': 623, 'arcgis-imageserver': 234, 'arcgis-vectortileserver': 40})
- Distinct title+publisher (rough dedupe): 33524

## Metadata quality
- Abstract of 50+ chars: 27%
- Any licence/constraints text: 45%; recognised open licence: 7%
- Keywords: 66%; WGS84 extent: 100%
- Linked to a catalogue record: 17%
- Code-like layer titles (before using catalogue names): 37%; junk-flagged: 6%
- **Declares an ISO theme (directly or via INSPIRE/DGU crosswalk): 10%** {'none': 55467, 'keyword': 5497, 'theme-field': 556}
- Publisher type: {'public-body': 20671, 'local-gov': 12957, 'unknown': 7400, 'international': 6499, 'academic': 4007, 'regional-gov': 3510, 'central-gov': 3198, 'business': 1790, 'civil-society': 1488}

## Datasets (endpoints grouped)
- **Datasets: 38327** from 61520 endpoints; passing: 10616
- Reachable by more than one protocol: 7261
- Endpoints per dataset: {1: 26672, 2: 6837, 3: 2343, 4: 945, 5: 406, 6: 300, 7: 57, 8: 767}
- Grouping rules used: {'title-extent': 6807, 'ogc-name': 3245, 'arcgis-pair': 1796, 'arcgis-ogc': 1319, 'catalogue': 144}
- Role (all / passing): {'data': 38210, 'imagery': 57, 'elevation': 46, 'basemap': 14} / {'data': 10570, 'elevation': 32, 'imagery': 12, 'basemap': 2}
- Capabilities offered: {'render': 27887, 'query': 26027, 'download': 12232, 'feature-info': 9382, 'tiles': 3142, 'pixels': 605, 'time': 161, 'catalog': 93, 'raster-functions': 70, 'multidimensional': 17}

## Coverage and detail
- Coverage level (from extent): {'local': 23208, 'national': 19181, 'regional': 12584, 'global': 4190, 'continental': 2103, 'unknown': 254}
- Extent source: {'declared': 58657, 'measured': 2863}; suspect-extent flags: {'grid-default': 3981, 'shared-default': 3346, 'world': 1366, 'too-big-local': 1000}
- Endpoints that allow browser access (CORS): 54643
- Detail estimate source: {'none': 55826, 'display': 3450, 'stated': 1999, 'pixel-size': 234, 'tile-cache': 11}
- Detail level, all layers: {'unknown': 55826, '1:100k': 1437, '1:500k': 1392, '1:2M': 1026, '1:25k': 1024, '1:5k': 498, 'coarser': 317}
- Detail level, passing layers: {'unknown': 11686, '1:100k': 772, '1:500k': 429, '1:25k': 426, '1:2M': 267, 'coarser': 199, '1:5k': 153}

## Liveness (sample, up to 2 layers per service)
- {'unchecked': 57804, 'ok': 3375, 'fail': 322, 'empty': 19}
- Returns data: 0.908; returns data or valid empty: 0.913

## Quality bar
- **Pass: 13932 layers (23%)**; distinct among passing: 9834
- Score median 60.0; bands {'[0, 40)': 3354, '[40, 50)': 4138, '[50, 60)': 22624, '[60, 70)': 10684, '[70, 80)': 10657, '[80, 101)': 10063}

## Size
- layers.parquet: 11.47 MB for 61520 layers

## Top service errors
- HTTP N: 2155
- robots.txt disallows: 587
- {'code': N, 'message': 'Invalid URL', 'details': ['Invalid: 311
- TimeoutError: : 210
- parse: ValueError: exception report: 101
- {'code': N, 'message': 'Token Required', 'messageCode': 'G: 25
- ClientOSError: [Errno N] Connection reset by peer: 25
- {'code': N, 'message': 'Token Required', 'details': []}: 18

AI-tag agreement is not in this run (needs the API key); it comes next.
