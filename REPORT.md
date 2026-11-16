# Spike report: CANZ

Run time 73.4 min; 141727 HTTP requests; 3894 blocked by robots.txt.

## Coverage
- Catalogues harvested: 365/507 (records linking to services: 50883)
- ArcGIS server roots reachable: 476/629
- Services crawled OK: 51914/58143 (skipped for time: 0); by type {'arcgis-imageserver': 2529, 'arcgis-vectortileserver': 348, 'wfs': 636, 'wms': 2698, 'arcgis-mapserver': 21973, 'arcgis-featureserver': 23625, 'wmts': 29, 'wcs': 76}
- **Layers found: 215341** ({'arcgis-mapserver': 144372, 'arcgis-featureserver': 34638, 'wms': 23747, 'wfs': 7856, 'arcgis-imageserver': 2003, 'wmts': 1240, 'wcs': 1215, 'arcgis-vectortileserver': 270})
- Distinct title+publisher (rough dedupe): 127335

## Metadata quality
- Abstract of 50+ chars: 38%
- Any licence/constraints text: 50%; recognised open licence: 5%
- Keywords: 66%; WGS84 extent: 97%
- Linked to a catalogue record: 14%
- Code-like layer titles (before using catalogue names): 19%; junk-flagged: 0%
- **Declares an ISO theme (directly or via INSPIRE/DGU crosswalk): 5%** {'none': 204488, 'keyword': 10853}
- Publisher type: {'local-gov': 74150, 'public-body': 49506, 'regional-gov': 36653, 'unknown': 30792, 'academic': 11217, 'central-gov': 8950, 'business': 2761, 'civil-society': 1312}

## Datasets (endpoints grouped)
- **Datasets: 143072** from 215341 endpoints; passing: 52214
- Reachable by more than one protocol: 18330
- Endpoints per dataset: {1: 104494, 2: 24887, 3: 6382, 4: 3145, 5: 661, 6: 820, 7: 342, 8: 2341}
- Grouping rules used: {'title-extent': 25021, 'arcgis-pair': 11127, 'arcgis-ogc': 5082, 'ogc-name': 787, 'catalogue': 208}
- Role (all / passing): {'data': 139643, 'imagery': 2262, 'basemap': 681, 'elevation': 486} / {'data': 51477, 'imagery': 529, 'elevation': 123, 'basemap': 85}
- Capabilities offered: {'render': 115559, 'query': 112623, 'download': 22434, 'feature-info': 18224, 'tiles': 11934, 'time': 1644, 'pixels': 1265, 'catalog': 949, 'raster-functions': 299, 'multidimensional': 58}

## Coverage and detail
- Coverage level (from extent): {'local': 75892, 'regional': 61005, 'national': 36360, 'continental': 22040, 'global': 14227, 'unknown': 5817}
- Extent source: {'declared': 204888, 'measured': 10453}; suspect-extent flags: {'shared-default': 10933, 'world': 4262, 'too-big-local': 4217}
- Endpoints that allow browser access (CORS): 197638
- Detail estimate source: {'none': 154339, 'display': 47183, 'stated': 11684, 'pixel-size': 1993, 'tile-cache': 142}
- Detail level, all layers: {'unknown': 154339, '1:100k': 16168, '1:500k': 15241, '1:25k': 11498, '1:5k': 9825, '1:2M': 7130, 'coarser': 1140}
- Detail level, passing layers: {'unknown': 47568, '1:500k': 7358, '1:100k': 6845, '1:2M': 4468, '1:25k': 4329, '1:5k': 3105, 'coarser': 979}

## Liveness (sample, up to 2 layers per service)
- {'unchecked': 203916, 'ok': 10963, 'fail': 281, 'empty': 181}
- Returns data: 0.96; returns data or valid empty: 0.975

## Quality bar
- **Pass: 74652 layers (35%)**; distinct among passing: 48425
- Score median 63.0; bands {'[0, 40)': 12881, '[40, 50)': 11138, '[50, 60)': 51567, '[60, 70)': 48864, '[70, 80)': 36000, '[80, 101)': 54891}

## Size
- layers.parquet: 46.48 MB for 215341 layers

## Top service errors
- robots.txt disallows: 3826
- {'code': N, 'details': 'error', 'message': 'HTTP N Not F: 502
- HTTP N: 483
- {'code': N, 'message': 'Token Required', 'details': []}: 380
- TimeoutError: : 324
- {'code': N, 'details': [], 'message': 'Token Required'}: 109
- {'code': N, 'details': [], 'message': 'Service not found'}: 99
- {'code': N, 'details': [], 'message': 'Service not found.': 64

AI-tag agreement is not in this run (needs the API key); it comes next.
