# Spike report: AFRICA

Run time 76.3 min; 21193 HTTP requests; 19 blocked by robots.txt.

## Coverage
- Catalogues harvested: 54/86 (records linking to services: 1002)
- ArcGIS server roots reachable: 77/102
- Services crawled OK: 5478/6481 (skipped for time: 0); by type {'arcgis-imageserver': 54, 'arcgis-vectortileserver': 11, 'arcgis-mapserver': 2488, 'arcgis-featureserver': 2754, 'wmts': 27, 'wcs': 41, 'wfs': 47, 'wms': 56}
- **Layers found: 24370** ({'arcgis-mapserver': 11540, 'arcgis-featureserver': 5087, 'wms': 3909, 'wmts': 1820, 'wfs': 1580, 'wcs': 371, 'arcgis-imageserver': 52, 'arcgis-vectortileserver': 11})
- Distinct title+publisher (rough dedupe): 15081

## Metadata quality
- Abstract of 50+ chars: 25%
- Any licence/constraints text: 20%; recognised open licence: 1%
- Keywords: 59%; WGS84 extent: 98%
- Linked to a catalogue record: 2%
- Code-like layer titles (before using catalogue names): 35%; junk-flagged: 0%
- **Declares an ISO theme (directly or via INSPIRE/DGU crosswalk): 1%** {'none': 24025, 'keyword': 345}
- Publisher type: {'central-gov': 9590, 'local-gov': 5130, 'international': 4004, 'unknown': 2226, 'regional-gov': 1996, 'business': 550, 'academic': 484, 'civil-society': 325, 'public-body': 65}

## Datasets (endpoints grouped)
- **Datasets: 17647** from 24370 endpoints; passing: 8688
- Reachable by more than one protocol: 3775
- Endpoints per dataset: {1: 12941, 2: 3800, 3: 444, 4: 221, 5: 83, 6: 27, 7: 12, 8: 119}
- Grouping rules used: {'arcgis-pair': 2354, 'title-extent': 1486, 'ogc-name': 1180}
- Role (all / passing): {'data': 17375, 'imagery': 238, 'elevation': 24, 'basemap': 10} / {'data': 8585, 'imagery': 86, 'elevation': 11, 'basemap': 6}
- Capabilities offered: {'render': 13263, 'query': 11865, 'feature-info': 3893, 'download': 3138, 'tiles': 2233, 'pixels': 371, 'time': 359, 'catalog': 47, 'raster-functions': 6}

## Coverage and detail
- Coverage level (from extent): {'local': 6259, 'regional': 6230, 'national': 5064, 'continental': 4638, 'global': 1775, 'unknown': 404}
- Extent source: {'declared': 23357, 'measured': 1013}; suspect-extent flags: {'world': 1513, 'shared-default': 474, 'too-big-local': 437}
- Endpoints that allow browser access (CORS): 20468
- Detail estimate source: {'none': 21452, 'display': 2132, 'stated': 733, 'pixel-size': 52, 'tile-cache': 1}
- Detail level, all layers: {'unknown': 21452, '1:25k': 1008, '1:100k': 824, '1:500k': 529, '1:5k': 428, '1:2M': 124, 'coarser': 5}
- Detail level, passing layers: {'unknown': 11644, '1:100k': 456, '1:500k': 415, '1:25k': 331, '1:5k': 202, '1:2M': 82, 'coarser': 5}

## Liveness (sample, up to 2 layers per service)
- {'unchecked': 19473, 'ok': 4164, 'fail': 449, 'empty': 284}
- Returns data: 0.85; returns data or valid empty: 0.908

## Quality bar
- **Pass: 13135 layers (54%)**; distinct among passing: 7292
- Score median 60.0; bands {'[0, 40)': 1397, '[40, 50)': 846, '[50, 60)': 7860, '[60, 70)': 8969, '[70, 80)': 3058, '[80, 101)': 2240}

## Size
- layers.parquet: 3.98 MB for 24370 layers

## Top service errors
- HTTP N: 184
- {'code': N, 'message': 'Token Required', 'messageCode': 'S: 147
- {'code': N, 'message': 'Token Required', 'details': []}: 137
- TimeoutError: : 100
- {'code': N, 'message': 'Error creating object to be cached: 21
- {'code': N, 'message': 'Error handling service request :0x: 14
- {'code': N, 'message': 'Error handling service request :GI: 9
- {'code': N, 'message': "User couldn't access this resource: 8

AI-tag agreement is not in this run (needs the API key); it comes next.
