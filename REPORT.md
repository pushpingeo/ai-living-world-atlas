# Spike report: US

Run time 299.0 min; 382766 HTTP requests; 181 blocked by robots.txt.

## Coverage
- Catalogues harvested: 158/2076 (records linking to services: 2441)
- ArcGIS server roots reachable: 1561/2516
- Services crawled OK: 120240/125994 (skipped for time: 889); by type {'arcgis-imageserver': 8022, 'arcgis-vectortileserver': 2029, 'arcgis-mapserver': 76444, 'arcgis-featureserver': 33662, 'wms': 38, 'wcs': 15, 'wfs': 25, 'wmts': 5}
- **Layers found: 678876** ({'arcgis-mapserver': 554849, 'arcgis-featureserver': 90928, 'wms': 12690, 'arcgis-imageserver': 8006, 'wcs': 7577, 'wfs': 2344, 'arcgis-vectortileserver': 2020, 'wmts': 462})
- Distinct title+publisher (rough dedupe): 376946

## Metadata quality
- Abstract of 50+ chars: 20%
- Any licence/constraints text: 38%; recognised open licence: 0%
- Keywords: 68%; WGS84 extent: 99%
- Linked to a catalogue record: 0%
- Code-like layer titles (before using catalogue names): 25%; junk-flagged: 1%
- **Declares an ISO theme (directly or via INSPIRE/DGU crosswalk): 4%** {'none': 648769, 'keyword': 30107}
- Publisher type: {'local-gov': 330516, 'regional-gov': 187337, 'academic': 74721, 'central-gov': 45031, 'business': 15899, 'public-body': 10738, 'civil-society': 9724, 'unknown': 4845, 'international': 65}

## Datasets (endpoints grouped)
- **Datasets: 453204** from 678876 endpoints; passing: 70831
- Reachable by more than one protocol: 68261
- Endpoints per dataset: {1: 322962, 2: 93412, 3: 13403, 4: 10226, 5: 3607, 6: 2918, 7: 974, 8: 5702}
- Grouping rules used: {'title-extent': 75854, 'arcgis-pair': 60310, 'ogc-name': 986, 'arcgis-ogc': 8, 'catalogue': 1}
- Role (all / passing): {'data': 439373, 'imagery': 9431, 'basemap': 2643, 'elevation': 1757} / {'data': 69584, 'imagery': 598, 'basemap': 342, 'elevation': 307}
- Capabilities offered: {'render': 429393, 'query': 340264, 'tiles': 73468, 'download': 29450, 'feature-info': 11199, 'pixels': 7799, 'time': 4068, 'catalog': 4056, 'raster-functions': 1976, 'multidimensional': 41}

## Coverage and detail
- Coverage level (from extent): {'local': 291011, 'regional': 235244, 'national': 84481, 'global': 42377, 'continental': 21383, 'unknown': 4380}
- Extent source: {'declared': 632513, 'measured': 46363}; suspect-extent flags: {'shared-default': 38301, 'world': 24836, 'too-big-local': 21506, 'grid-default': 2}
- Endpoints that allow browser access (CORS): 663435
- Detail estimate source: {'none': 525521, 'display': 125977, 'stated': 19093, 'pixel-size': 7990, 'tile-cache': 295}
- Detail level, all layers: {'unknown': 525521, '1:25k': 49976, '1:100k': 34967, '1:5k': 26749, '1:500k': 26137, '1:2M': 11271, 'coarser': 4255}
- Detail level, passing layers: {'unknown': 75667, '1:25k': 9316, '1:100k': 5875, '1:500k': 5490, '1:2M': 3238, '1:5k': 3228, 'coarser': 847}

## Liveness (sample, up to 2 layers per service)
- {'unchecked': 621725, 'ok': 55362, 'empty': 981, 'fail': 808}
- Returns data: 0.969; returns data or valid empty: 0.986

## Quality bar
- **Pass: 103661 layers (15%)**; distinct among passing: 63169
- Score median 60.0; bands {'[0, 40)': 8657, '[40, 50)': 44008, '[50, 60)': 187507, '[60, 70)': 191628, '[70, 80)': 150788, '[80, 101)': 96288}

## Size
- layers.parquet: 135.71 MB for 678876 layers

## Top service errors
- TimeoutError: : 1861
- {'code': N, 'message': 'Token Required', 'details': []}: 994
- skipped: time budget: 889
- {'code': N, 'details': 'error', 'message': 'HTTP N Not F: 408
- {'code': N, 'message': 'Error handling service request :Co: 204
- {'code': N, 'message': 'Error handling service request :GI: 202
- {'code': N, 'message': 'Error handling service request :0x: 195
- HTTP N: 138

AI-tag agreement is not in this run (needs the API key); it comes next.
