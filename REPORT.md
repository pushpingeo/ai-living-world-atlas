# Development-plan collections

- 1,225,385 datasets look like local plans; 466,865 of them passed the quality bar.
- Grouped 466,089 of those into **1,849 collections** (one per council, 3+ plans).
- Passing datasets: 582,975 before, **118,735 after**.

Largest collections:

- Development plans – Stadt Stuttgart (DE): 17,959 plans
- Development plans – MGIPU-Zavod za prostorni razvoj/Ministry of Construction and Physical Planning-Institute for Spatial Development (HR): 12,873 plans
- Development plans – Stadt Celle (DE): 8,622 plans
- Development plans – Stadt Weener (DE): 7,178 plans
- Development plans – Stadt Leer (Ostfriesland) (DE): 6,714 plans
- Development plans – LVGL (DE): 4,939 plans
- Development plans – Gemeinde Moormerland (DE): 4,894 plans
- Development plans – Stadt Aalen (DE): 4,252 plans
- Development plans – Gemeinde Ganderkesee (DE): 4,092 plans
- Development plans – Stadt Heilbronn (DE): 4,019 plans
- Development plans – Landkreis Osterholz (DE): 4,018 plans
- Development plans – Stadt Königslutter am Elm (DE): 3,842 plans
- Development plans – Stadt Pattensen (DE): 3,385 plans
- Development plans – Samtgemeinde Velpke (DE): 3,097 plans
- Development plans – Stadt Kirchheim unter Teck (DE): 2,933 plans

# Spike report: INSPIRE (concatenated shards)

- **Layers: 3441647; datasets: 2570156**; dataset totals summed over shards: {"total": 2570156, "passing": 859538, "multi_protocol": 178724, "detail_known_passing": 104562}
- Shards were not regrouped against each other (too big to hold in memory), so a dataset published on two hosts in different shards appears twice.

Per-shard reports follow.

## shard-0


Run time 137.6 min; 44891 HTTP requests; 4787 blocked by robots.txt.

## Coverage
- Catalogues harvested: 1/1 (records linking to services: 681441)
- ArcGIS server roots reachable: 17/26
- Services crawled OK: 29338/37512 (skipped for time: 0); by type {'arcgis-imageserver': 134, 'arcgis-vectortileserver': 56, 'arcgis-mapserver': 3371, 'arcgis-featureserver': 1915, 'wfs': 10456, 'wms': 13355, 'wcs': 36, 'wmts': 15}
- **Layers found: 168697** ({'wms': 80739, 'wfs': 65343, 'arcgis-mapserver': 18537, 'arcgis-featureserver': 2915, 'wcs': 778, 'wmts': 195, 'arcgis-imageserver': 134, 'arcgis-vectortileserver': 56})
- Distinct title+publisher (rough dedupe): 78053

## Metadata quality
- Abstract of 50+ chars: 40%
- Any licence/constraints text: 80%; recognised open licence: 20%
- Keywords: 31%; WGS84 extent: 99%
- Linked to a catalogue record: 13%
- Code-like layer titles (before using catalogue names): 53%; junk-flagged: 0%
- **Declares an ISO theme (directly or via INSPIRE/DGU crosswalk): 4%** {'none': 161164, 'theme-field': 6109, 'keyword': 1424}
- Publisher type: {'public-body': 168655, 'international': 42}

## Datasets (endpoints grouped)
- **Datasets: 123573** from 168697 endpoints; passing: 40226
- Reachable by more than one protocol: 10065
- Endpoints per dataset: {1: 102728, 2: 13608, 3: 1731, 4: 1379, 5: 810, 6: 960, 7: 622, 8: 1735}
- Grouping rules used: {'title-extent': 12609, 'ogc-name': 5669, 'arcgis-pair': 2390, 'arcgis-ogc': 484, 'catalogue': 120}
- Role (all / passing): {'data': 123117, 'imagery': 430, 'basemap': 13, 'elevation': 13} / {'data': 40092, 'imagery': 116, 'basemap': 10, 'elevation': 8}
- Capabilities offered: {'render': 90074, 'feature-info': 67940, 'query': 51108, 'download': 41265, 'tiles': 2024, 'pixels': 697, 'time': 138, 'catalog': 71, 'raster-functions': 39, 'multidimensional': 14}

## Coverage and detail
- Coverage level (from extent): {'local': 93653, 'global': 39048, 'regional': 20936, 'national': 13395, 'unknown': 854, 'continental': 811}
- Extent source: {'declared': 167148, 'measured': 1549}; suspect-extent flags: {'world': 38026, 'shared-default': 29412, 'grid-default': 11}
- Endpoints that allow browser access (CORS): 160607
- Detail estimate source: {'none': 151202, 'display': 12871, 'stated': 4442, 'pixel-size': 127, 'tile-cache': 55}
- Detail level, all layers: {'unknown': 151202, '1:25k': 4914, '1:500k': 4311, '1:5k': 3701, '1:100k': 3334, '1:2M': 811, 'coarser': 424}
- Detail level, passing layers: {'unknown': 42365, '1:500k': 1797, '1:5k': 1260, '1:25k': 947, '1:100k': 771, '1:2M': 114, 'coarser': 8}

## Liveness (sample, up to 2 layers per service)
- {'unchecked': 164775, 'ok': 2206, 'fail': 1711, 'empty': 5}
- Returns data: 0.562; returns data or valid empty: 0.564

## Quality bar
- **Pass: 47262 layers (28%)**; distinct among passing: 27838
- Score median 70.0; bands {'[40, 50)': 4481, '[50, 60)': 19920, '[60, 70)': 59526, '[70, 80)': 51177, '[80, 101)': 33593}

## Size
- layers.parquet: 24.63 MB for 168697 layers

## Top service errors
- robots.txt disallows: 4784
- HTTP N: 1940
- parse: ParseError: not well-formed (invalid token): line 84,: 568
- TimeoutError: : 281
- parse: ParseError: not well-formed (invalid token): line 1, : 120
- parse: ValueError: exception report: 78
- ClientConnectorDNSError: Cannot connect to host mapserveur.a: 56
- ClientConnectorCertificateError: Cannot connect to host serv: 56

AI-tag agreement is not in this run (needs the API key); it comes next.

## shard-1


Run time 173.1 min; 45594 HTTP requests; 4885 blocked by robots.txt.

## Coverage
- Catalogues harvested: 1/1 (records linking to services: 681441)
- ArcGIS server roots reachable: 20/31
- Services crawled OK: 29141/37474 (skipped for time: 0); by type {'arcgis-imageserver': 165, 'arcgis-mapserver': 3873, 'wfs': 10293, 'arcgis-featureserver': 1405, 'wms': 13320, 'arcgis-vectortileserver': 52, 'wmts': 14, 'wcs': 19}
- **Layers found: 177296** ({'wms': 85479, 'wfs': 69036, 'arcgis-mapserver': 19706, 'arcgis-featureserver': 1796, 'wcs': 752, 'wmts': 310, 'arcgis-imageserver': 165, 'arcgis-vectortileserver': 52})
- Distinct title+publisher (rough dedupe): 81291

## Metadata quality
- Abstract of 50+ chars: 41%
- Any licence/constraints text: 81%; recognised open licence: 20%
- Keywords: 31%; WGS84 extent: 99%
- Linked to a catalogue record: 13%
- Code-like layer titles (before using catalogue names): 52%; junk-flagged: 0%
- **Declares an ISO theme (directly or via INSPIRE/DGU crosswalk): 4%** {'none': 170691, 'theme-field': 6223, 'keyword': 382}
- Publisher type: {'public-body': 177244, 'international': 52}

## Datasets (endpoints grouped)
- **Datasets: 131244** from 177296 endpoints; passing: 46511
- Reachable by more than one protocol: 9526
- Endpoints per dataset: {1: 111234, 2: 11952, 3: 2086, 4: 1470, 5: 1408, 6: 674, 7: 424, 8: 1996}
- Grouping rules used: {'title-extent': 12218, 'ogc-name': 5876, 'arcgis-pair': 1666, 'arcgis-ogc': 475, 'catalogue': 118}
- Role (all / passing): {'data': 130664, 'imagery': 516, 'elevation': 55, 'basemap': 9} / {'data': 46292, 'imagery': 206, 'elevation': 11, 'basemap': 2}
- Capabilities offered: {'render': 96099, 'feature-info': 72700, 'query': 53932, 'download': 42302, 'tiles': 1707, 'pixels': 766, 'time': 95, 'catalog': 34, 'raster-functions': 22, 'multidimensional': 1}

## Coverage and detail
- Coverage level (from extent): {'local': 96890, 'global': 40334, 'regional': 23457, 'national': 14318, 'unknown': 1155, 'continental': 1142}
- Extent source: {'declared': 174933, 'measured': 2363}; suspect-extent flags: {'world': 39966, 'shared-default': 32138, 'grid-default': 49}
- Endpoints that allow browser access (CORS): 169327
- Detail estimate source: {'none': 158780, 'display': 13870, 'stated': 4482, 'pixel-size': 164}
- Detail level, all layers: {'unknown': 158780, '1:25k': 5099, '1:5k': 4242, '1:500k': 4196, '1:100k': 3630, '1:2M': 1154, 'coarser': 195}
- Detail level, passing layers: {'unknown': 48444, '1:500k': 1930, '1:5k': 1253, '1:25k': 1172, '1:100k': 1161, '1:2M': 712, 'coarser': 162}

## Liveness (sample, up to 2 layers per service)
- {'unchecked': 173352, 'ok': 2119, 'fail': 1819, 'empty': 6}
- Returns data: 0.537; returns data or valid empty: 0.539

## Quality bar
- **Pass: 54834 layers (31%)**; distinct among passing: 33873
- Score median 70.0; bands {'[40, 50)': 5223, '[50, 60)': 19667, '[60, 70)': 61860, '[70, 80)': 51698, '[80, 101)': 38848}

## Size
- layers.parquet: 25.42 MB for 177296 layers

## Top service errors
- robots.txt disallows: 4881
- HTTP N: 1941
- parse: ParseError: not well-formed (invalid token): line 84,: 592
- TimeoutError: : 275
- parse: ParseError: not well-formed (invalid token): line 1, : 131
- parse: ValueError: exception report: 98
- ClientConnectorCertificateError: Cannot connect to host serv: 68
- ClientConnectorDNSError: Cannot connect to host mapserveur.a: 52

AI-tag agreement is not in this run (needs the API key); it comes next.

## shard-10


Run time 173.9 min; 42363 HTTP requests; 4981 blocked by robots.txt.

## Coverage
- Catalogues harvested: 1/1 (records linking to services: 681441)
- ArcGIS server roots reachable: 17/31
- Services crawled OK: 27987/36438 (skipped for time: 0); by type {'arcgis-imageserver': 205, 'arcgis-mapserver': 3086, 'arcgis-featureserver': 995, 'wfs': 10248, 'wms': 13356, 'wmts': 18, 'arcgis-vectortileserver': 52, 'wcs': 27}
- **Layers found: 176993** ({'wms': 87842, 'wfs': 65926, 'arcgis-mapserver': 20754, 'arcgis-featureserver': 1489, 'wcs': 523, 'arcgis-imageserver': 205, 'wmts': 202, 'arcgis-vectortileserver': 52})
- Distinct title+publisher (rough dedupe): 86417

## Metadata quality
- Abstract of 50+ chars: 39%
- Any licence/constraints text: 79%; recognised open licence: 19%
- Keywords: 31%; WGS84 extent: 99%
- Linked to a catalogue record: 13%
- Code-like layer titles (before using catalogue names): 52%; junk-flagged: 0%
- **Declares an ISO theme (directly or via INSPIRE/DGU crosswalk): 4%** {'none': 170479, 'theme-field': 6028, 'keyword': 486}
- Publisher type: {'public-body': 176969, 'international': 24}

## Datasets (endpoints grouped)
- **Datasets: 135821** from 176993 endpoints; passing: 45949
- Reachable by more than one protocol: 8366
- Endpoints per dataset: {1: 116993, 2: 12083, 3: 1514, 4: 1555, 5: 901, 6: 689, 7: 255, 8: 1831}
- Grouping rules used: {'title-extent': 12235, 'ogc-name': 5322, 'arcgis-pair': 1414, 'arcgis-ogc': 176, 'catalogue': 129}
- Role (all / passing): {'data': 134983, 'imagery': 821, 'elevation': 12, 'basemap': 5} / {'data': 45692, 'imagery': 250, 'elevation': 4, 'basemap': 3}
- Capabilities offered: {'render': 100135, 'feature-info': 76052, 'query': 54168, 'download': 42281, 'tiles': 1098, 'pixels': 533, 'time': 173, 'catalog': 65, 'raster-functions': 31, 'multidimensional': 1}

## Coverage and detail
- Coverage level (from extent): {'local': 98362, 'global': 37808, 'regional': 23207, 'national': 14992, 'unknown': 1332, 'continental': 1292}
- Extent source: {'declared': 175449, 'measured': 1544}; suspect-extent flags: {'world': 36899, 'shared-default': 33898, 'grid-default': 12}
- Endpoints that allow browser access (CORS): 168905
- Detail estimate source: {'none': 158618, 'display': 13767, 'stated': 4405, 'pixel-size': 203}
- Detail level, all layers: {'unknown': 158618, '1:25k': 5381, '1:500k': 4443, '1:5k': 3920, '1:100k': 3544, '1:2M': 896, 'coarser': 191}
- Detail level, passing layers: {'unknown': 45602, '1:500k': 1926, '1:5k': 1302, '1:100k': 1039, '1:25k': 924, '1:2M': 149, 'coarser': 57}

## Liveness (sample, up to 2 layers per service)
- {'unchecked': 173051, 'ok': 2081, 'fail': 1857, 'empty': 4}
- Returns data: 0.528; returns data or valid empty: 0.529

## Quality bar
- **Pass: 50999 layers (29%)**; distinct among passing: 33408
- Score median 68.0; bands {'[40, 50)': 4080, '[50, 60)': 23917, '[60, 70)': 61068, '[70, 80)': 54178, '[80, 101)': 33750}

## Size
- layers.parquet: 24.58 MB for 176993 layers

## Top service errors
- robots.txt disallows: 4979
- HTTP N: 2031
- parse: ParseError: not well-formed (invalid token): line 84,: 550
- TimeoutError: : 259
- parse: ParseError: not well-formed (invalid token): line 1, : 160
- parse: ValueError: exception report: 91
- ClientConnectorCertificateError: Cannot connect to host serv: 60
- ClientConnectorDNSError: Cannot connect to host mapserveur.a: 50

AI-tag agreement is not in this run (needs the API key); it comes next.

## shard-11


Run time 175.7 min; 43139 HTTP requests; 4658 blocked by robots.txt.

## Coverage
- Catalogues harvested: 1/1 (records linking to services: 681441)
- ArcGIS server roots reachable: 16/30
- Services crawled OK: 27940/35971 (skipped for time: 0); by type {'arcgis-vectortileserver': 55, 'arcgis-imageserver': 100, 'arcgis-mapserver': 3058, 'wms': 13305, 'wfs': 10248, 'arcgis-featureserver': 1128, 'wcs': 31, 'wmts': 15}
- **Layers found: 171218** ({'wms': 86861, 'wfs': 64479, 'arcgis-mapserver': 16798, 'arcgis-featureserver': 2003, 'wcs': 662, 'wmts': 260, 'arcgis-imageserver': 100, 'arcgis-vectortileserver': 55})
- Distinct title+publisher (rough dedupe): 78708

## Metadata quality
- Abstract of 50+ chars: 38%
- Any licence/constraints text: 83%; recognised open licence: 22%
- Keywords: 32%; WGS84 extent: 99%
- Linked to a catalogue record: 13%
- Code-like layer titles (before using catalogue names): 55%; junk-flagged: 0%
- **Declares an ISO theme (directly or via INSPIRE/DGU crosswalk): 4%** {'none': 164542, 'theme-field': 6141, 'keyword': 535}
- Publisher type: {'public-body': 171201, 'international': 17}

## Datasets (endpoints grouped)
- **Datasets: 132485** from 171218 endpoints; passing: 40937
- Reachable by more than one protocol: 8884
- Endpoints per dataset: {1: 114319, 2: 12334, 3: 1410, 4: 884, 5: 521, 6: 477, 7: 1322, 8: 1218}
- Grouping rules used: {'title-extent': 11087, 'ogc-name': 5386, 'arcgis-pair': 1824, 'arcgis-ogc': 308, 'catalogue': 123}
- Role (all / passing): {'data': 132192, 'imagery': 256, 'elevation': 27, 'basemap': 10} / {'data': 40736, 'imagery': 186, 'elevation': 12, 'basemap': 3}
- Capabilities offered: {'render': 97171, 'feature-info': 75191, 'query': 51886, 'download': 42158, 'tiles': 1622, 'time': 751, 'pixels': 619, 'catalog': 47, 'raster-functions': 15, 'multidimensional': 1}

## Coverage and detail
- Coverage level (from extent): {'local': 94861, 'global': 36355, 'regional': 22019, 'national': 14945, 'unknown': 1774, 'continental': 1264}
- Extent source: {'declared': 168914, 'measured': 2304}; suspect-extent flags: {'shared-default': 37825, 'world': 35862, 'grid-default': 30}
- Endpoints that allow browser access (CORS): 163287
- Detail estimate source: {'none': 154504, 'display': 11978, 'stated': 4639, 'pixel-size': 97}
- Detail level, all layers: {'unknown': 154504, '1:25k': 4882, '1:500k': 4193, '1:5k': 3669, '1:100k': 2862, '1:2M': 911, 'coarser': 197}
- Detail level, passing layers: {'unknown': 41508, '1:500k': 2003, '1:5k': 1415, '1:100k': 982, '1:25k': 952, '1:2M': 156, 'coarser': 15}

## Liveness (sample, up to 2 layers per service)
- {'unchecked': 167265, 'ok': 2141, 'fail': 1805, 'empty': 7}
- Returns data: 0.542; returns data or valid empty: 0.543

## Quality bar
- **Pass: 47031 layers (28%)**; distinct among passing: 28380
- Score median 70.0; bands {'[40, 50)': 3948, '[50, 60)': 17253, '[60, 70)': 59880, '[70, 80)': 57105, '[80, 101)': 33032}

## Size
- layers.parquet: 23.68 MB for 171218 layers

## Top service errors
- robots.txt disallows: 4655
- HTTP N: 1922
- parse: ParseError: not well-formed (invalid token): line 84,: 602
- TimeoutError: : 273
- parse: ParseError: not well-formed (invalid token): line 1, : 132
- parse: ValueError: exception report: 82
- ClientConnectorDNSError: Cannot connect to host mapserveur.a: 60
- ClientConnectorCertificateError: Cannot connect to host serv: 50

AI-tag agreement is not in this run (needs the API key); it comes next.

## shard-12


Run time 153.9 min; 43041 HTTP requests; 4965 blocked by robots.txt.

## Coverage
- Catalogues harvested: 1/1 (records linking to services: 681441)
- ArcGIS server roots reachable: 20/32
- Services crawled OK: 28224/36751 (skipped for time: 0); by type {'arcgis-vectortileserver': 52, 'arcgis-mapserver': 3146, 'arcgis-featureserver': 1048, 'wfs': 10332, 'wms': 13368, 'arcgis-imageserver': 229, 'wcs': 38, 'wmts': 11}
- **Layers found: 166191** ({'wms': 75313, 'wfs': 69557, 'arcgis-mapserver': 18712, 'arcgis-featureserver': 1523, 'wcs': 599, 'arcgis-imageserver': 229, 'wmts': 206, 'arcgis-vectortileserver': 52})
- Distinct title+publisher (rough dedupe): 72158

## Metadata quality
- Abstract of 50+ chars: 38%
- Any licence/constraints text: 81%; recognised open licence: 20%
- Keywords: 30%; WGS84 extent: 99%
- Linked to a catalogue record: 14%
- Code-like layer titles (before using catalogue names): 56%; junk-flagged: 0%
- **Declares an ISO theme (directly or via INSPIRE/DGU crosswalk): 4%** {'none': 159658, 'theme-field': 6193, 'keyword': 340}
- Publisher type: {'public-body': 166140, 'international': 51}

## Datasets (endpoints grouped)
- **Datasets: 120307** from 166191 endpoints; passing: 39086
- Reachable by more than one protocol: 8260
- Endpoints per dataset: {1: 100931, 2: 11547, 3: 1922, 4: 1244, 5: 1263, 6: 827, 7: 437, 8: 2136}
- Grouping rules used: {'title-extent': 12832, 'ogc-name': 5262, 'arcgis-pair': 1338, 'arcgis-ogc': 202, 'catalogue': 123}
- Role (all / passing): {'data': 119853, 'imagery': 411, 'elevation': 40, 'basemap': 3} / {'data': 38776, 'imagery': 289, 'elevation': 20, 'basemap': 1}
- Capabilities offered: {'render': 86336, 'feature-info': 64269, 'query': 51275, 'download': 40556, 'tiles': 1075, 'pixels': 571, 'time': 132, 'catalog': 68, 'raster-functions': 33, 'multidimensional': 1}

## Coverage and detail
- Coverage level (from extent): {'local': 87981, 'global': 42871, 'regional': 19554, 'national': 14148, 'unknown': 837, 'continental': 800}
- Extent source: {'declared': 164424, 'measured': 1767}; suspect-extent flags: {'world': 42562, 'shared-default': 30786, 'grid-default': 15}
- Endpoints that allow browser access (CORS): 157154
- Detail estimate source: {'none': 150325, 'display': 11792, 'stated': 3850, 'pixel-size': 224}
- Detail level, all layers: {'unknown': 150325, '1:25k': 4427, '1:500k': 3978, '1:5k': 3580, '1:100k': 3289, '1:2M': 575, 'coarser': 17}
- Detail level, passing layers: {'unknown': 39536, '1:500k': 2032, '1:5k': 1222, '1:100k': 999, '1:25k': 747, '1:2M': 114, 'coarser': 6}

## Liveness (sample, up to 2 layers per service)
- {'unchecked': 162246, 'ok': 2076, 'fail': 1865, 'empty': 4}
- Returns data: 0.526; returns data or valid empty: 0.527

## Quality bar
- **Pass: 44656 layers (27%)**; distinct among passing: 27285
- Score median 68.0; bands {'[40, 50)': 4010, '[50, 60)': 20630, '[60, 70)': 60561, '[70, 80)': 48697, '[80, 101)': 32293}

## Size
- layers.parquet: 22.81 MB for 166191 layers

## Top service errors
- robots.txt disallows: 4964
- HTTP N: 2037
- parse: ParseError: not well-formed (invalid token): line 84,: 576
- TimeoutError: : 267
- parse: ParseError: not well-formed (invalid token): line 1, : 149
- parse: ValueError: exception report: 89
- ClientConnectorDNSError: Cannot connect to host mapserveur.a: 64
- ClientConnectorCertificateError: Cannot connect to host serv: 60

AI-tag agreement is not in this run (needs the API key); it comes next.

## shard-13


Run time 127.3 min; 42836 HTTP requests; 4842 blocked by robots.txt.

## Coverage
- Catalogues harvested: 1/1 (records linking to services: 681441)
- ArcGIS server roots reachable: 22/32
- Services crawled OK: 28057/36365 (skipped for time: 0); by type {'arcgis-imageserver': 198, 'arcgis-vectortileserver': 54, 'arcgis-mapserver': 3177, 'wfs': 10214, 'arcgis-featureserver': 1077, 'wms': 13295, 'wcs': 26, 'wmts': 16}
- **Layers found: 168497** ({'wms': 78848, 'wfs': 66297, 'arcgis-mapserver': 20187, 'arcgis-featureserver': 2168, 'wcs': 557, 'arcgis-imageserver': 198, 'wmts': 188, 'arcgis-vectortileserver': 54})
- Distinct title+publisher (rough dedupe): 78476

## Metadata quality
- Abstract of 50+ chars: 39%
- Any licence/constraints text: 80%; recognised open licence: 19%
- Keywords: 32%; WGS84 extent: 99%
- Linked to a catalogue record: 14%
- Code-like layer titles (before using catalogue names): 53%; junk-flagged: 0%
- **Declares an ISO theme (directly or via INSPIRE/DGU crosswalk): 5%** {'none': 160438, 'theme-field': 6075, 'keyword': 1984}
- Publisher type: {'public-body': 168473, 'international': 24}

## Datasets (endpoints grouped)
- **Datasets: 126162** from 168497 endpoints; passing: 41695
- Reachable by more than one protocol: 9063
- Endpoints per dataset: {1: 106363, 2: 12816, 3: 1808, 4: 916, 5: 1925, 6: 314, 7: 255, 8: 1765}
- Grouping rules used: {'title-extent': 12638, 'ogc-name': 5354, 'arcgis-pair': 1995, 'arcgis-ogc': 181, 'catalogue': 119}
- Role (all / passing): {'data': 125749, 'imagery': 374, 'elevation': 34, 'basemap': 5} / {'data': 41545, 'imagery': 136, 'elevation': 11, 'basemap': 3}
- Capabilities offered: {'render': 90738, 'feature-info': 65644, 'query': 54570, 'download': 42488, 'tiles': 1637, 'pixels': 570, 'time': 454, 'catalog': 67, 'raster-functions': 32, 'multidimensional': 1}

## Coverage and detail
- Coverage level (from extent): {'local': 93314, 'global': 39099, 'regional': 20149, 'national': 13822, 'unknown': 1119, 'continental': 994}
- Extent source: {'declared': 166801, 'measured': 1696}; suspect-extent flags: {'world': 38302, 'shared-default': 28676, 'grid-default': 4}
- Endpoints that allow browser access (CORS): 159400
- Detail estimate source: {'none': 151131, 'display': 12875, 'stated': 4295, 'pixel-size': 196}
- Detail level, all layers: {'unknown': 151131, '1:25k': 4889, '1:500k': 4328, '1:100k': 3743, '1:5k': 3481, '1:2M': 531, 'coarser': 394}
- Detail level, passing layers: {'unknown': 42475, '1:500k': 1916, '1:25k': 1332, '1:5k': 1121, '1:100k': 934, '1:2M': 127, 'coarser': 4}

## Liveness (sample, up to 2 layers per service)
- {'unchecked': 164585, 'ok': 2167, 'fail': 1743, 'empty': 2}
- Returns data: 0.554; returns data or valid empty: 0.554

## Quality bar
- **Pass: 47909 layers (28%)**; distinct among passing: 29766
- Score median 68.0; bands {'[40, 50)': 4505, '[50, 60)': 22207, '[60, 70)': 58561, '[70, 80)': 47412, '[80, 101)': 35812}

## Size
- layers.parquet: 24.23 MB for 168497 layers

## Top service errors
- robots.txt disallows: 4841
- HTTP N: 2023
- parse: ParseError: not well-formed (invalid token): line 84,: 572
- TimeoutError: : 268
- parse: ParseError: not well-formed (invalid token): line 1, : 133
- parse: ValueError: exception report: 77
- ClientConnectorCertificateError: Cannot connect to host serv: 59
- ClientConnectorDNSError: Cannot connect to host mapserveur.a: 51

AI-tag agreement is not in this run (needs the API key); it comes next.

## shard-14


Run time 166.8 min; 44294 HTTP requests; 4796 blocked by robots.txt.

## Coverage
- Catalogues harvested: 1/1 (records linking to services: 681441)
- ArcGIS server roots reachable: 23/34
- Services crawled OK: 28683/36931 (skipped for time: 0); by type {'wfs': 10399, 'wms': 13346, 'arcgis-mapserver': 3659, 'arcgis-featureserver': 1084, 'arcgis-imageserver': 108, 'arcgis-vectortileserver': 54, 'wcs': 22, 'wmts': 11}
- **Layers found: 181463** ({'wms': 83309, 'wfs': 66952, 'arcgis-mapserver': 28601, 'arcgis-featureserver': 1770, 'wcs': 474, 'wmts': 195, 'arcgis-imageserver': 108, 'arcgis-vectortileserver': 54})
- Distinct title+publisher (rough dedupe): 84207

## Metadata quality
- Abstract of 50+ chars: 39%
- Any licence/constraints text: 75%; recognised open licence: 19%
- Keywords: 33%; WGS84 extent: 100%
- Linked to a catalogue record: 12%
- Code-like layer titles (before using catalogue names): 50%; junk-flagged: 0%
- **Declares an ISO theme (directly or via INSPIRE/DGU crosswalk): 4%** {'none': 173941, 'theme-field': 6102, 'keyword': 1420}
- Publisher type: {'public-body': 181414, 'international': 49}

## Datasets (endpoints grouped)
- **Datasets: 135113** from 181463 endpoints; passing: 46120
- Reachable by more than one protocol: 8401
- Endpoints per dataset: {1: 114216, 2: 12928, 3: 2190, 4: 1352, 5: 1414, 6: 760, 7: 241, 8: 2012}
- Grouping rules used: {'title-extent': 14227, 'ogc-name': 5212, 'arcgis-pair': 1533, 'catalogue': 125, 'arcgis-ogc': 124}
- Role (all / passing): {'data': 134810, 'imagery': 279, 'elevation': 20, 'basemap': 4} / {'data': 45993, 'imagery': 120, 'elevation': 6, 'basemap': 1}
- Capabilities offered: {'render': 98988, 'feature-info': 69543, 'query': 59220, 'download': 42942, 'tiles': 3348, 'time': 1084, 'pixels': 474, 'catalog': 18, 'raster-functions': 17, 'multidimensional': 14}

## Coverage and detail
- Coverage level (from extent): {'local': 95191, 'global': 38445, 'regional': 24650, 'national': 21063, 'continental': 1399, 'unknown': 715}
- Extent source: {'declared': 179605, 'measured': 1858}; suspect-extent flags: {'world': 37475, 'shared-default': 30991, 'grid-default': 11}
- Endpoints that allow browser access (CORS): 173233
- Detail estimate source: {'none': 164844, 'display': 12024, 'stated': 4494, 'pixel-size': 101}
- Detail level, all layers: {'unknown': 164844, '1:25k': 4800, '1:500k': 4163, '1:5k': 3474, '1:100k': 3192, '1:2M': 550, 'coarser': 440}
- Detail level, passing layers: {'unknown': 47845, '1:500k': 1851, '1:25k': 1245, '1:5k': 1170, '1:100k': 953, '1:2M': 98, 'coarser': 27}

## Liveness (sample, up to 2 layers per service)
- {'unchecked': 177512, 'ok': 2120, 'fail': 1811, 'empty': 20}
- Returns data: 0.537; returns data or valid empty: 0.542

## Quality bar
- **Pass: 53189 layers (29%)**; distinct among passing: 33623
- Score median 68.0; bands {'[40, 50)': 4833, '[50, 60)': 29050, '[60, 70)': 60253, '[70, 80)': 51664, '[80, 101)': 35663}

## Size
- layers.parquet: 26.15 MB for 181463 layers

## Top service errors
- robots.txt disallows: 4793
- HTTP N: 1974
- parse: ParseError: not well-formed (invalid token): line 84,: 600
- TimeoutError: : 267
- parse: ParseError: not well-formed (invalid token): line 1, : 148
- parse: ValueError: exception report: 70
- ClientConnectorCertificateError: Cannot connect to host serv: 64
- ClientConnectorDNSError: Cannot connect to host mapserveur.a: 49

AI-tag agreement is not in this run (needs the API key); it comes next.

## shard-15


Run time 175.7 min; 44366 HTTP requests; 4727 blocked by robots.txt.

## Coverage
- Catalogues harvested: 1/1 (records linking to services: 681441)
- ArcGIS server roots reachable: 22/30
- Services crawled OK: 28479/36591 (skipped for time: 0); by type {'arcgis-imageserver': 94, 'arcgis-mapserver': 3488, 'wfs': 10487, 'wms': 13220, 'arcgis-featureserver': 1083, 'wcs': 30, 'arcgis-vectortileserver': 57, 'wmts': 20}
- **Layers found: 169042** ({'wms': 82379, 'wfs': 61549, 'arcgis-mapserver': 22723, 'arcgis-featureserver': 1368, 'wcs': 603, 'wmts': 269, 'arcgis-imageserver': 94, 'arcgis-vectortileserver': 57})
- Distinct title+publisher (rough dedupe): 78407

## Metadata quality
- Abstract of 50+ chars: 40%
- Any licence/constraints text: 78%; recognised open licence: 21%
- Keywords: 33%; WGS84 extent: 99%
- Linked to a catalogue record: 14%
- Code-like layer titles (before using catalogue names): 53%; junk-flagged: 0%
- **Declares an ISO theme (directly or via INSPIRE/DGU crosswalk): 4%** {'none': 162441, 'theme-field': 6158, 'keyword': 443}
- Publisher type: {'public-body': 169017, 'international': 25}

## Datasets (endpoints grouped)
- **Datasets: 128346** from 169042 endpoints; passing: 42785
- Reachable by more than one protocol: 8174
- Endpoints per dataset: {1: 108957, 2: 12508, 3: 1878, 4: 1802, 5: 671, 6: 370, 7: 628, 8: 1532}
- Grouping rules used: {'title-extent': 13234, 'ogc-name': 5122, 'arcgis-pair': 1124, 'arcgis-ogc': 208, 'catalogue': 124}
- Role (all / passing): {'data': 127980, 'imagery': 318, 'elevation': 37, 'basemap': 11} / {'data': 42612, 'imagery': 154, 'elevation': 14, 'basemap': 5}
- Capabilities offered: {'render': 94864, 'feature-info': 69130, 'query': 53650, 'download': 39928, 'tiles': 2742, 'pixels': 564, 'time': 148, 'catalog': 48, 'raster-functions': 15, 'multidimensional': 1}

## Coverage and detail
- Coverage level (from extent): {'local': 94663, 'global': 34080, 'regional': 21427, 'national': 17082, 'unknown': 928, 'continental': 862}
- Extent source: {'declared': 166615, 'measured': 2427}; suspect-extent flags: {'world': 33580, 'shared-default': 33390, 'grid-default': 2}
- Endpoints that allow browser access (CORS): 160629
- Detail estimate source: {'none': 151709, 'display': 12828, 'stated': 4413, 'pixel-size': 92}
- Detail level, all layers: {'unknown': 151709, '1:25k': 4952, '1:500k': 4567, '1:5k': 3663, '1:100k': 3592, '1:2M': 521, 'coarser': 38}
- Detail level, passing layers: {'unknown': 43351, '1:500k': 2262, '1:5k': 1232, '1:100k': 1071, '1:25k': 1002, '1:2M': 158, 'coarser': 29}

## Liveness (sample, up to 2 layers per service)
- {'unchecked': 165087, 'ok': 2139, 'fail': 1798, 'empty': 18}
- Returns data: 0.541; returns data or valid empty: 0.545

## Quality bar
- **Pass: 49105 layers (29%)**; distinct among passing: 30558
- Score median 70.0; bands {'[40, 50)': 4645, '[50, 60)': 22525, '[60, 70)': 55578, '[70, 80)': 51841, '[80, 101)': 34453}

## Size
- layers.parquet: 24.34 MB for 169042 layers

## Top service errors
- robots.txt disallows: 4726
- HTTP N: 1921
- parse: ParseError: not well-formed (invalid token): line 84,: 610
- TimeoutError: : 303
- parse: ParseError: not well-formed (invalid token): line 1, : 113
- parse: ValueError: exception report: 77
- ClientConnectorDNSError: Cannot connect to host mapserveur.a: 66
- ClientConnectorCertificateError: Cannot connect to host serv: 44

AI-tag agreement is not in this run (needs the API key); it comes next.

## shard-16


Run time 132.3 min; 41175 HTTP requests; 4847 blocked by robots.txt.

## Coverage
- Catalogues harvested: 1/1 (records linking to services: 681441)
- ArcGIS server roots reachable: 17/28
- Services crawled OK: 27440/35692 (skipped for time: 0); by type {'arcgis-imageserver': 111, 'arcgis-vectortileserver': 53, 'wms': 13213, 'wfs': 10288, 'arcgis-mapserver': 2645, 'arcgis-featureserver': 1065, 'wcs': 44, 'wmts': 21}
- **Layers found: 162717** ({'wms': 80456, 'wfs': 63634, 'arcgis-mapserver': 15959, 'arcgis-featureserver': 1684, 'wcs': 588, 'wmts': 232, 'arcgis-imageserver': 111, 'arcgis-vectortileserver': 53})
- Distinct title+publisher (rough dedupe): 77969

## Metadata quality
- Abstract of 50+ chars: 40%
- Any licence/constraints text: 80%; recognised open licence: 19%
- Keywords: 32%; WGS84 extent: 99%
- Linked to a catalogue record: 14%
- Code-like layer titles (before using catalogue names): 54%; junk-flagged: 0%
- **Declares an ISO theme (directly or via INSPIRE/DGU crosswalk): 5%** {'none': 154967, 'theme-field': 6238, 'keyword': 1512}
- Publisher type: {'public-body': 162686, 'international': 31}

## Datasets (endpoints grouped)
- **Datasets: 123888** from 162717 endpoints; passing: 40323
- Reachable by more than one protocol: 8757
- Endpoints per dataset: {1: 105724, 2: 12158, 3: 1632, 4: 1060, 5: 644, 6: 307, 7: 425, 8: 1938}
- Grouping rules used: {'title-extent': 10987, 'ogc-name': 5685, 'arcgis-pair': 1566, 'arcgis-ogc': 176, 'catalogue': 122}
- Role (all / passing): {'data': 123340, 'imagery': 507, 'elevation': 33, 'basemap': 8} / {'data': 40131, 'imagery': 178, 'elevation': 9, 'basemap': 5}
- Capabilities offered: {'render': 89221, 'feature-info': 67788, 'query': 51137, 'download': 41835, 'tiles': 1780, 'pixels': 466, 'time': 243, 'catalog': 55, 'raster-functions': 19}

## Coverage and detail
- Coverage level (from extent): {'local': 90478, 'global': 36194, 'regional': 19043, 'national': 14991, 'unknown': 1007, 'continental': 1004}
- Extent source: {'declared': 161349, 'measured': 1368}; suspect-extent flags: {'world': 35435, 'shared-default': 31457, 'grid-default': 102}
- Endpoints that allow browser access (CORS): 153240
- Detail estimate source: {'none': 145846, 'display': 11055, 'stated': 5708, 'pixel-size': 108}
- Detail level, all layers: {'unknown': 145846, '1:25k': 4527, '1:500k': 4056, '1:5k': 4016, '1:100k': 3188, '1:2M': 640, 'coarser': 444}
- Detail level, passing layers: {'unknown': 40554, '1:500k': 1815, '1:5k': 1681, '1:100k': 1066, '1:25k': 889, '1:2M': 148, 'coarser': 48}

## Liveness (sample, up to 2 layers per service)
- {'unchecked': 158788, 'ok': 2118, 'fail': 1804, 'empty': 7}
- Returns data: 0.539; returns data or valid empty: 0.541

## Quality bar
- **Pass: 46201 layers (28%)**; distinct among passing: 28616
- Score median 70.0; bands {'[40, 50)': 5175, '[50, 60)': 18266, '[60, 70)': 56501, '[70, 80)': 49739, '[80, 101)': 33036}

## Size
- layers.parquet: 23.46 MB for 162717 layers

## Top service errors
- robots.txt disallows: 4845
- HTTP N: 1926
- parse: ParseError: not well-formed (invalid token): line 84,: 622
- TimeoutError: : 292
- parse: ParseError: not well-formed (invalid token): line 1, : 133
- parse: ValueError: exception report: 66
- ClientConnectorDNSError: Cannot connect to host mapserveur.a: 53
- ClientConnectorCertificateError: Cannot connect to host serv: 50

AI-tag agreement is not in this run (needs the API key); it comes next.

## shard-17


Run time 173.8 min; 46463 HTTP requests; 4883 blocked by robots.txt.

## Coverage
- Catalogues harvested: 1/1 (records linking to services: 681441)
- ArcGIS server roots reachable: 19/29
- Services crawled OK: 29105/37451 (skipped for time: 0); by type {'arcgis-mapserver': 3964, 'wfs': 10223, 'wms': 13246, 'arcgis-featureserver': 1384, 'arcgis-imageserver': 181, 'arcgis-vectortileserver': 59, 'wcs': 28, 'wmts': 20}
- **Layers found: 178770** ({'wms': 86343, 'wfs': 62899, 'arcgis-mapserver': 25753, 'arcgis-featureserver': 2805, 'wcs': 513, 'wmts': 217, 'arcgis-imageserver': 181, 'arcgis-vectortileserver': 59})
- Distinct title+publisher (rough dedupe): 83221

## Metadata quality
- Abstract of 50+ chars: 38%
- Any licence/constraints text: 77%; recognised open licence: 21%
- Keywords: 34%; WGS84 extent: 100%
- Linked to a catalogue record: 13%
- Code-like layer titles (before using catalogue names): 51%; junk-flagged: 0%
- **Declares an ISO theme (directly or via INSPIRE/DGU crosswalk): 4%** {'none': 172114, 'theme-field': 6274, 'keyword': 382}
- Publisher type: {'public-body': 178687, 'international': 83}

## Datasets (endpoints grouped)
- **Datasets: 135263** from 178770 endpoints; passing: 42902
- Reachable by more than one protocol: 9520
- Endpoints per dataset: {1: 115164, 2: 13443, 3: 1586, 4: 1345, 5: 552, 6: 551, 7: 460, 8: 2162}
- Grouping rules used: {'title-extent': 12338, 'ogc-name': 5837, 'arcgis-pair': 1985, 'arcgis-ogc': 255, 'catalogue': 120}
- Role (all / passing): {'data': 134891, 'imagery': 344, 'elevation': 25, 'basemap': 3} / {'data': 42707, 'imagery': 182, 'elevation': 12, 'basemap': 1}
- Capabilities offered: {'render': 100673, 'feature-info': 73139, 'query': 54738, 'download': 41305, 'tiles': 2690, 'pixels': 481, 'time': 133, 'catalog': 62, 'raster-functions': 31, 'multidimensional': 1}

## Coverage and detail
- Coverage level (from extent): {'local': 98520, 'global': 36636, 'regional': 26033, 'national': 14341, 'continental': 2562, 'unknown': 678}
- Extent source: {'declared': 175657, 'measured': 3113}; suspect-extent flags: {'world': 35600, 'shared-default': 34086}
- Endpoints that allow browser access (CORS): 169006
- Detail estimate source: {'none': 157895, 'display': 15442, 'stated': 5199, 'pixel-size': 179, 'tile-cache': 55}
- Detail level, all layers: {'unknown': 157895, '1:25k': 6709, '1:500k': 4781, '1:100k': 4520, '1:5k': 3711, '1:2M': 1144, 'coarser': 10}
- Detail level, passing layers: {'unknown': 44155, '1:500k': 1818, '1:25k': 1316, '1:5k': 1234, '1:100k': 1185, '1:2M': 137, 'coarser': 6}

## Liveness (sample, up to 2 layers per service)
- {'unchecked': 174862, 'ok': 2143, 'fail': 1759, 'empty': 6}
- Returns data: 0.548; returns data or valid empty: 0.55

## Quality bar
- **Pass: 49851 layers (28%)**; distinct among passing: 30928
- Score median 68.0; bands {'[40, 50)': 5243, '[50, 60)': 25613, '[60, 70)': 58678, '[70, 80)': 52912, '[80, 101)': 36324}

## Size
- layers.parquet: 25.37 MB for 178770 layers

## Top service errors
- robots.txt disallows: 4881
- HTTP N: 2015
- parse: ParseError: not well-formed (invalid token): line 84,: 605
- TimeoutError: : 234
- parse: ParseError: not well-formed (invalid token): line 1, : 129
- parse: ValueError: exception report: 84
- ClientConnectorDNSError: Cannot connect to host mapserveur.a: 56
- ClientConnectorCertificateError: Cannot connect to host serv: 52

AI-tag agreement is not in this run (needs the API key); it comes next.

## shard-18


Run time 164.6 min; 43070 HTTP requests; 4664 blocked by robots.txt.

## Coverage
- Catalogues harvested: 1/1 (records linking to services: 681441)
- ArcGIS server roots reachable: 17/27
- Services crawled OK: 27789/35802 (skipped for time: 0); by type {'arcgis-featureserver': 1024, 'arcgis-mapserver': 3178, 'wfs': 10338, 'wms': 13099, 'wcs': 26, 'arcgis-vectortileserver': 59, 'wmts': 18, 'arcgis-imageserver': 47}
- **Layers found: 167334** ({'wms': 80515, 'wfs': 62343, 'arcgis-mapserver': 21672, 'arcgis-featureserver': 1995, 'wcs': 504, 'wmts': 199, 'arcgis-vectortileserver': 59, 'arcgis-imageserver': 47})
- Distinct title+publisher (rough dedupe): 78894

## Metadata quality
- Abstract of 50+ chars: 40%
- Any licence/constraints text: 78%; recognised open licence: 19%
- Keywords: 33%; WGS84 extent: 99%
- Linked to a catalogue record: 14%
- Code-like layer titles (before using catalogue names): 50%; junk-flagged: 0%
- **Declares an ISO theme (directly or via INSPIRE/DGU crosswalk): 4%** {'none': 160686, 'theme-field': 6253, 'keyword': 395}
- Publisher type: {'public-body': 167302, 'international': 32}

## Datasets (endpoints grouped)
- **Datasets: 125261** from 167334 endpoints; passing: 42969
- Reachable by more than one protocol: 8764
- Endpoints per dataset: {1: 106250, 2: 11524, 3: 2258, 4: 1178, 5: 1375, 6: 521, 7: 691, 8: 1464}
- Grouping rules used: {'title-extent': 12094, 'ogc-name': 5813, 'arcgis-pair': 1266, 'arcgis-ogc': 212, 'catalogue': 133}
- Role (all / passing): {'data': 124994, 'imagery': 233, 'elevation': 24, 'basemap': 10} / {'data': 42807, 'imagery': 146, 'elevation': 10, 'basemap': 6}
- Capabilities offered: {'render': 92471, 'feature-info': 67737, 'query': 52873, 'download': 39322, 'tiles': 1539, 'pixels': 466, 'time': 107, 'catalog': 25, 'raster-functions': 21, 'multidimensional': 1}

## Coverage and detail
- Coverage level (from extent): {'local': 92765, 'global': 35535, 'regional': 23275, 'national': 13860, 'continental': 1059, 'unknown': 840}
- Extent source: {'declared': 164937, 'measured': 2397}; suspect-extent flags: {'world': 34574, 'shared-default': 30546, 'grid-default': 26}
- Endpoints that allow browser access (CORS): 158564
- Detail estimate source: {'none': 149356, 'display': 13765, 'stated': 4169, 'pixel-size': 44}
- Detail level, all layers: {'unknown': 149356, '1:25k': 5536, '1:500k': 4235, '1:100k': 3918, '1:5k': 3725, '1:2M': 506, 'coarser': 58}
- Detail level, passing layers: {'unknown': 44534, '1:500k': 1974, '1:5k': 1256, '1:25k': 1190, '1:100k': 1008, '1:2M': 114, 'coarser': 34}

## Liveness (sample, up to 2 layers per service)
- {'unchecked': 163382, 'ok': 2088, 'fail': 1859, 'empty': 5}
- Returns data: 0.528; returns data or valid empty: 0.53

## Quality bar
- **Pass: 50110 layers (30%)**; distinct among passing: 30472
- Score median 70.0; bands {'[40, 50)': 4677, '[50, 60)': 22931, '[60, 70)': 55841, '[70, 80)': 48649, '[80, 101)': 35236}

## Size
- layers.parquet: 24.24 MB for 167334 layers

## Top service errors
- robots.txt disallows: 4661
- HTTP N: 1953
- parse: ParseError: not well-formed (invalid token): line 84,: 552
- TimeoutError: : 271
- parse: ParseError: not well-formed (invalid token): line 1, : 127
- parse: ValueError: exception report: 72
- ClientConnectorCertificateError: Cannot connect to host serv: 49
- ClientConnectorDNSError: Cannot connect to host mapserveur.a: 46

AI-tag agreement is not in this run (needs the API key); it comes next.

## shard-19


Run time 172.8 min; 43959 HTTP requests; 4679 blocked by robots.txt.

## Coverage
- Catalogues harvested: 1/1 (records linking to services: 681441)
- ArcGIS server roots reachable: 21/33
- Services crawled OK: 28270/36305 (skipped for time: 0); by type {'arcgis-vectortileserver': 52, 'wfs': 10338, 'arcgis-mapserver': 3481, 'wms': 13173, 'wcs': 34, 'arcgis-featureserver': 1041, 'arcgis-imageserver': 143, 'wmts': 8}
- **Layers found: 166881** ({'wms': 77365, 'wfs': 62778, 'arcgis-mapserver': 24070, 'arcgis-featureserver': 1548, 'wcs': 730, 'wmts': 195, 'arcgis-imageserver': 143, 'arcgis-vectortileserver': 52})
- Distinct title+publisher (rough dedupe): 78769

## Metadata quality
- Abstract of 50+ chars: 40%
- Any licence/constraints text: 78%; recognised open licence: 19%
- Keywords: 32%; WGS84 extent: 99%
- Linked to a catalogue record: 14%
- Code-like layer titles (before using catalogue names): 49%; junk-flagged: 0%
- **Declares an ISO theme (directly or via INSPIRE/DGU crosswalk): 4%** {'none': 160492, 'theme-field': 6062, 'keyword': 327}
- Publisher type: {'public-body': 166847, 'international': 34}

## Datasets (endpoints grouped)
- **Datasets: 125884** from 166881 endpoints; passing: 42218
- Reachable by more than one protocol: 8745
- Endpoints per dataset: {1: 106474, 2: 12443, 3: 1607, 4: 1511, 5: 1328, 6: 751, 7: 650, 8: 1120}
- Grouping rules used: {'title-extent': 12507, 'ogc-name': 5627, 'arcgis-pair': 1384, 'arcgis-ogc': 193, 'catalogue': 120}
- Role (all / passing): {'data': 125618, 'imagery': 223, 'elevation': 29, 'basemap': 14} / {'data': 42071, 'imagery': 125, 'elevation': 14, 'basemap': 8}
- Capabilities offered: {'render': 91459, 'feature-info': 64793, 'query': 55923, 'download': 41451, 'tiles': 1489, 'pixels': 646, 'time': 231, 'catalog': 66, 'raster-functions': 34, 'multidimensional': 1}

## Coverage and detail
- Coverage level (from extent): {'local': 90436, 'global': 35720, 'regional': 23065, 'national': 15809, 'unknown': 1061, 'continental': 790}
- Extent source: {'declared': 164511, 'measured': 2370}; suspect-extent flags: {'world': 34840, 'shared-default': 29744, 'grid-default': 12}
- Endpoints that allow browser access (CORS): 158734
- Detail estimate source: {'none': 148620, 'display': 13701, 'stated': 4417, 'pixel-size': 143}
- Detail level, all layers: {'unknown': 148620, '1:25k': 5260, '1:500k': 4428, '1:5k': 4002, '1:100k': 3976, '1:2M': 571, 'coarser': 24}
- Detail level, passing layers: {'unknown': 43559, '1:500k': 1981, '1:5k': 1366, '1:25k': 1276, '1:100k': 1084, '1:2M': 97, 'coarser': 23}

## Liveness (sample, up to 2 layers per service)
- {'unchecked': 162938, 'ok': 2161, 'fail': 1775, 'empty': 7}
- Returns data: 0.548; returns data or valid empty: 0.55

## Quality bar
- **Pass: 49386 layers (30%)**; distinct among passing: 30080
- Score median 70.0; bands {'[40, 50)': 4638, '[50, 60)': 23916, '[60, 70)': 54821, '[70, 80)': 48434, '[80, 101)': 35072}

## Size
- layers.parquet: 24.33 MB for 166881 layers

## Top service errors
- robots.txt disallows: 4676
- HTTP N: 1938
- parse: ParseError: not well-formed (invalid token): line 84,: 535
- TimeoutError: : 299
- parse: ParseError: not well-formed (invalid token): line 1, : 136
- parse: ValueError: exception report: 91
- ClientConnectorCertificateError: Cannot connect to host serv: 53
- ClientConnectorDNSError: Cannot connect to host mapserveur.a: 45

AI-tag agreement is not in this run (needs the API key); it comes next.

## shard-2


Run time 168.3 min; 42175 HTTP requests; 4812 blocked by robots.txt.

## Coverage
- Catalogues harvested: 1/1 (records linking to services: 681441)
- ArcGIS server roots reachable: 14/23
- Services crawled OK: 27401/35627 (skipped for time: 0); by type {'arcgis-imageserver': 58, 'arcgis-vectortileserver': 52, 'wfs': 10343, 'arcgis-mapserver': 2957, 'wms': 13011, 'arcgis-featureserver': 934, 'wmts': 15, 'wcs': 31}
- **Layers found: 165773** ({'wms': 82313, 'wfs': 64657, 'arcgis-mapserver': 16624, 'arcgis-featureserver': 1268, 'wcs': 610, 'wmts': 191, 'arcgis-imageserver': 58, 'arcgis-vectortileserver': 52})
- Distinct title+publisher (rough dedupe): 78087

## Metadata quality
- Abstract of 50+ chars: 42%
- Any licence/constraints text: 81%; recognised open licence: 21%
- Keywords: 32%; WGS84 extent: 100%
- Linked to a catalogue record: 14%
- Code-like layer titles (before using catalogue names): 52%; junk-flagged: 0%
- **Declares an ISO theme (directly or via INSPIRE/DGU crosswalk): 4%** {'none': 159194, 'theme-field': 6329, 'keyword': 250}
- Publisher type: {'public-body': 165757, 'international': 16}

## Datasets (endpoints grouped)
- **Datasets: 123827** from 165773 endpoints; passing: 44111
- Reachable by more than one protocol: 8639
- Endpoints per dataset: {1: 105334, 2: 11129, 3: 1806, 4: 1845, 5: 630, 6: 908, 7: 615, 8: 1560}
- Grouping rules used: {'title-extent': 11729, 'ogc-name': 5716, 'arcgis-pair': 1127, 'arcgis-ogc': 160, 'catalogue': 132}
- Role (all / passing): {'data': 123675, 'imagery': 124, 'elevation': 24, 'basemap': 4} / {'data': 44014, 'imagery': 85, 'elevation': 11, 'basemap': 1}
- Capabilities offered: {'render': 89468, 'feature-info': 68347, 'query': 51258, 'download': 41480, 'tiles': 1262, 'pixels': 568, 'time': 192, 'catalog': 42, 'raster-functions': 13, 'multidimensional': 1}

## Coverage and detail
- Coverage level (from extent): {'local': 93857, 'global': 36380, 'regional': 20043, 'national': 13900, 'continental': 912, 'unknown': 681}
- Extent source: {'declared': 163580, 'measured': 2193}; suspect-extent flags: {'world': 35813, 'shared-default': 31403, 'grid-default': 9}
- Endpoints that allow browser access (CORS): 156825
- Detail estimate source: {'none': 150442, 'display': 11233, 'stated': 4043, 'pixel-size': 55}
- Detail level, all layers: {'unknown': 150442, '1:500k': 4349, '1:25k': 4196, '1:5k': 3216, '1:100k': 3054, '1:2M': 448, 'coarser': 68}
- Detail level, passing layers: {'unknown': 47120, '1:500k': 2036, '1:5k': 1182, '1:25k': 1048, '1:100k': 1014, '1:2M': 123, 'coarser': 53}

## Liveness (sample, up to 2 layers per service)
- {'unchecked': 161825, 'ok': 2104, 'fail': 1836, 'empty': 8}
- Returns data: 0.533; returns data or valid empty: 0.535

## Quality bar
- **Pass: 52576 layers (32%)**; distinct among passing: 31906
- Score median 70.0; bands {'[40, 50)': 4282, '[50, 60)': 17523, '[60, 70)': 56360, '[70, 80)': 50740, '[80, 101)': 36868}

## Size
- layers.parquet: 23.81 MB for 165773 layers

## Top service errors
- robots.txt disallows: 4811
- HTTP N: 1923
- parse: ParseError: not well-formed (invalid token): line 84,: 605
- TimeoutError: : 248
- parse: ParseError: not well-formed (invalid token): line 1, : 147
- parse: ValueError: exception report: 91
- ClientConnectorCertificateError: Cannot connect to host serv: 58
- ClientConnectorDNSError: Cannot connect to host mapserveur.a: 52

AI-tag agreement is not in this run (needs the API key); it comes next.

## shard-3


Run time 129.2 min; 43166 HTTP requests; 4798 blocked by robots.txt.

## Coverage
- Catalogues harvested: 1/1 (records linking to services: 681441)
- ArcGIS server roots reachable: 19/24
- Services crawled OK: 28195/36440 (skipped for time: 0); by type {'wfs': 10173, 'wms': 13251, 'arcgis-mapserver': 3242, 'arcgis-featureserver': 1254, 'arcgis-vectortileserver': 53, 'arcgis-imageserver': 171, 'wcs': 29, 'wmts': 22}
- **Layers found: 169444** ({'wms': 81991, 'wfs': 67530, 'arcgis-mapserver': 17076, 'arcgis-featureserver': 2051, 'wcs': 374, 'wmts': 198, 'arcgis-imageserver': 171, 'arcgis-vectortileserver': 53})
- Distinct title+publisher (rough dedupe): 77026

## Metadata quality
- Abstract of 50+ chars: 40%
- Any licence/constraints text: 79%; recognised open licence: 21%
- Keywords: 31%; WGS84 extent: 100%
- Linked to a catalogue record: 13%
- Code-like layer titles (before using catalogue names): 53%; junk-flagged: 0%
- **Declares an ISO theme (directly or via INSPIRE/DGU crosswalk): 4%** {'none': 162995, 'theme-field': 6085, 'keyword': 364}
- Publisher type: {'public-body': 169366, 'international': 78}

## Datasets (endpoints grouped)
- **Datasets: 124559** from 169444 endpoints; passing: 42780
- Reachable by more than one protocol: 9524
- Endpoints per dataset: {1: 104569, 2: 11984, 3: 2831, 4: 1098, 5: 890, 6: 656, 7: 612, 8: 1919}
- Grouping rules used: {'title-extent': 12221, 'ogc-name': 6198, 'arcgis-pair': 1791, 'arcgis-ogc': 261, 'catalogue': 77}
- Role (all / passing): {'data': 124124, 'imagery': 398, 'elevation': 30, 'basemap': 7} / {'data': 42660, 'imagery': 108, 'elevation': 7, 'basemap': 5}
- Capabilities offered: {'render': 90226, 'feature-info': 68765, 'query': 52262, 'download': 41603, 'tiles': 1369, 'pixels': 336, 'time': 296, 'catalog': 67, 'raster-functions': 34, 'multidimensional': 1}

## Coverage and detail
- Coverage level (from extent): {'local': 95204, 'global': 39159, 'regional': 18307, 'national': 15003, 'continental': 972, 'unknown': 799}
- Extent source: {'declared': 167822, 'measured': 1622}; suspect-extent flags: {'world': 38556, 'shared-default': 30800, 'grid-default': 43}
- Endpoints that allow browser access (CORS): 160871
- Detail estimate source: {'none': 153568, 'display': 11443, 'stated': 4262, 'pixel-size': 171}
- Detail level, all layers: {'unknown': 153568, '1:500k': 4376, '1:25k': 4088, '1:5k': 3876, '1:100k': 3054, '1:2M': 454, 'coarser': 28}
- Detail level, passing layers: {'unknown': 45320, '1:500k': 2119, '1:5k': 1399, '1:100k': 1033, '1:25k': 810, '1:2M': 96, 'coarser': 26}

## Liveness (sample, up to 2 layers per service)
- {'unchecked': 165516, 'ok': 2103, 'fail': 1818, 'empty': 7}
- Returns data: 0.535; returns data or valid empty: 0.537

## Quality bar
- **Pass: 50803 layers (30%)**; distinct among passing: 30936
- Score median 68.0; bands {'[40, 50)': 4553, '[50, 60)': 21063, '[60, 70)': 59254, '[70, 80)': 49001, '[80, 101)': 35573}

## Size
- layers.parquet: 23.87 MB for 169444 layers

## Top service errors
- robots.txt disallows: 4796
- HTTP N: 1970
- parse: ParseError: not well-formed (invalid token): line 84,: 600
- TimeoutError: : 263
- parse: ParseError: not well-formed (invalid token): line 1, : 111
- parse: ValueError: exception report: 77
- ClientConnectorCertificateError: Cannot connect to host serv: 64
- ClientConnectorDNSError: Cannot connect to host mapserveur.a: 55

AI-tag agreement is not in this run (needs the API key); it comes next.

## shard-4


Run time 166.5 min; 43541 HTTP requests; 4666 blocked by robots.txt.

## Coverage
- Catalogues harvested: 1/1 (records linking to services: 681441)
- ArcGIS server roots reachable: 17/24
- Services crawled OK: 28241/36418 (skipped for time: 0); by type {'arcgis-vectortileserver': 50, 'wms': 13249, 'arcgis-imageserver': 236, 'wfs': 10390, 'arcgis-mapserver': 3277, 'wcs': 29, 'arcgis-featureserver': 995, 'wmts': 15}
- **Layers found: 167884** ({'wms': 77929, 'wfs': 70161, 'arcgis-mapserver': 17351, 'arcgis-featureserver': 1308, 'wcs': 652, 'arcgis-imageserver': 236, 'wmts': 197, 'arcgis-vectortileserver': 50})
- Distinct title+publisher (rough dedupe): 74086

## Metadata quality
- Abstract of 50+ chars: 39%
- Any licence/constraints text: 82%; recognised open licence: 22%
- Keywords: 30%; WGS84 extent: 99%
- Linked to a catalogue record: 14%
- Code-like layer titles (before using catalogue names): 55%; junk-flagged: 0%
- **Declares an ISO theme (directly or via INSPIRE/DGU crosswalk): 4%** {'none': 161052, 'theme-field': 6339, 'keyword': 493}
- Publisher type: {'public-body': 167780, 'international': 104}

## Datasets (endpoints grouped)
- **Datasets: 122362** from 167884 endpoints; passing: 40647
- Reachable by more than one protocol: 8615
- Endpoints per dataset: {1: 102661, 2: 12213, 3: 1801, 4: 1249, 5: 1353, 6: 313, 7: 421, 8: 2351}
- Grouping rules used: {'title-extent': 13014, 'ogc-name': 5462, 'arcgis-pair': 1255, 'arcgis-ogc': 170, 'catalogue': 131}
- Role (all / passing): {'data': 121870, 'imagery': 443, 'elevation': 44, 'basemap': 5} / {'data': 40501, 'imagery': 112, 'elevation': 31, 'basemap': 3}
- Capabilities offered: {'render': 87521, 'feature-info': 65327, 'query': 51712, 'download': 41838, 'tiles': 1539, 'pixels': 661, 'time': 131, 'catalog': 47, 'raster-functions': 15, 'multidimensional': 13}

## Coverage and detail
- Coverage level (from extent): {'local': 91447, 'global': 42392, 'regional': 18968, 'national': 13329, 'unknown': 996, 'continental': 752}
- Extent source: {'declared': 165660, 'measured': 2224}; suspect-extent flags: {'world': 41946, 'shared-default': 32875, 'grid-default': 12}
- Endpoints that allow browser access (CORS): 160216
- Detail estimate source: {'none': 151503, 'display': 12223, 'stated': 3931, 'pixel-size': 227}
- Detail level, all layers: {'unknown': 151503, '1:25k': 4984, '1:500k': 4021, '1:5k': 3717, '1:100k': 3134, '1:2M': 507, 'coarser': 18}
- Detail level, passing layers: {'unknown': 42073, '1:500k': 1946, '1:5k': 1287, '1:100k': 1144, '1:25k': 981, '1:2M': 126, 'coarser': 11}

## Liveness (sample, up to 2 layers per service)
- {'unchecked': 163924, 'ok': 2174, 'fail': 1778, 'empty': 8}
- Returns data: 0.549; returns data or valid empty: 0.551

## Quality bar
- **Pass: 47568 layers (28%)**; distinct among passing: 28410
- Score median 70.0; bands {'[40, 50)': 3968, '[50, 60)': 18156, '[60, 70)': 60623, '[70, 80)': 50612, '[80, 101)': 34525}

## Size
- layers.parquet: 23.2 MB for 167884 layers

## Top service errors
- robots.txt disallows: 4664
- HTTP N: 2031
- parse: ParseError: not well-formed (invalid token): line 84,: 623
- TimeoutError: : 268
- parse: ParseError: not well-formed (invalid token): line 1, : 132
- parse: ValueError: exception report: 77
- ClientConnectorCertificateError: Cannot connect to host serv: 58
- ClientConnectorDNSError: Cannot connect to host mapserveur.a: 52

AI-tag agreement is not in this run (needs the API key); it comes next.

## shard-5


Run time 174.7 min; 42880 HTTP requests; 4780 blocked by robots.txt.

## Coverage
- Catalogues harvested: 1/1 (records linking to services: 681441)
- ArcGIS server roots reachable: 19/29
- Services crawled OK: 28280/36446 (skipped for time: 0); by type {'wms': 13453, 'arcgis-imageserver': 124, 'wfs': 10366, 'arcgis-mapserver': 3228, 'arcgis-featureserver': 1014, 'arcgis-vectortileserver': 52, 'wcs': 30, 'wmts': 13}
- **Layers found: 184264** ({'wms': 91324, 'wfs': 67077, 'arcgis-mapserver': 23549, 'arcgis-featureserver': 1417, 'wcs': 521, 'wmts': 200, 'arcgis-imageserver': 124, 'arcgis-vectortileserver': 52})
- Distinct title+publisher (rough dedupe): 83196

## Metadata quality
- Abstract of 50+ chars: 39%
- Any licence/constraints text: 79%; recognised open licence: 21%
- Keywords: 30%; WGS84 extent: 100%
- Linked to a catalogue record: 12%
- Code-like layer titles (before using catalogue names): 53%; junk-flagged: 0%
- **Declares an ISO theme (directly or via INSPIRE/DGU crosswalk): 4%** {'none': 177527, 'theme-field': 6119, 'keyword': 618}
- Publisher type: {'public-body': 184243, 'international': 21}

## Datasets (endpoints grouped)
- **Datasets: 138198** from 184264 endpoints; passing: 46751
- Reachable by more than one protocol: 8667
- Endpoints per dataset: {1: 117755, 2: 12973, 3: 2075, 4: 1095, 5: 942, 6: 582, 7: 452, 8: 2324}
- Grouping rules used: {'title-extent': 13534, 'ogc-name': 5741, 'arcgis-pair': 1308, 'arcgis-ogc': 186, 'catalogue': 128}
- Role (all / passing): {'data': 137815, 'imagery': 357, 'elevation': 21, 'basemap': 5} / {'data': 46567, 'imagery': 175, 'elevation': 7, 'basemap': 2}
- Capabilities offered: {'render': 103952, 'feature-info': 79481, 'query': 53707, 'download': 41270, 'tiles': 3376, 'pixels': 520, 'time': 245, 'catalog': 51, 'raster-functions': 16}

## Coverage and detail
- Coverage level (from extent): {'local': 103995, 'global': 40402, 'regional': 20858, 'national': 17090, 'continental': 1173, 'unknown': 746}
- Extent source: {'declared': 182697, 'measured': 1567}; suspect-extent flags: {'world': 39701, 'shared-default': 37213, 'grid-default': 6}
- Endpoints that allow browser access (CORS): 175723
- Detail estimate source: {'none': 166991, 'display': 13119, 'stated': 3977, 'pixel-size': 122, 'tile-cache': 55}
- Detail level, all layers: {'unknown': 166991, '1:25k': 4951, '1:500k': 4399, '1:5k': 3767, '1:100k': 3404, '1:2M': 731, 'coarser': 21}
- Detail level, passing layers: {'unknown': 48137, '1:500k': 2088, '1:5k': 1207, '1:100k': 853, '1:25k': 824, '1:2M': 162, 'coarser': 5}

## Liveness (sample, up to 2 layers per service)
- {'unchecked': 180301, 'ok': 2122, 'fail': 1824, 'empty': 17}
- Returns data: 0.535; returns data or valid empty: 0.54

## Quality bar
- **Pass: 53276 layers (29%)**; distinct among passing: 34131
- Score median 70.0; bands {'[40, 50)': 4990, '[50, 60)': 23960, '[60, 70)': 61121, '[70, 80)': 56044, '[80, 101)': 38149}

## Size
- layers.parquet: 25.12 MB for 184264 layers

## Top service errors
- robots.txt disallows: 4777
- HTTP N: 1947
- parse: ParseError: not well-formed (invalid token): line 84,: 592
- TimeoutError: : 252
- parse: ParseError: not well-formed (invalid token): line 1, : 122
- parse: ValueError: exception report: 80
- ClientConnectorDNSError: Cannot connect to host mapserveur.a: 52
- ClientConnectorCertificateError: Cannot connect to host serv: 48

AI-tag agreement is not in this run (needs the API key); it comes next.

## shard-6


Run time 129.4 min; 45521 HTTP requests; 4734 blocked by robots.txt.

## Coverage
- Catalogues harvested: 1/1 (records linking to services: 681441)
- ArcGIS server roots reachable: 19/30
- Services crawled OK: 29596/37757 (skipped for time: 0); by type {'wfs': 10356, 'arcgis-mapserver': 3528, 'arcgis-featureserver': 1999, 'wms': 13527, 'wcs': 25, 'wmts': 16, 'arcgis-vectortileserver': 59, 'arcgis-imageserver': 86}
- **Layers found: 176927** ({'wms': 81685, 'wfs': 69007, 'arcgis-mapserver': 19064, 'wcs': 3623, 'arcgis-featureserver': 3190, 'wmts': 213, 'arcgis-imageserver': 86, 'arcgis-vectortileserver': 59})
- Distinct title+publisher (rough dedupe): 82045

## Metadata quality
- Abstract of 50+ chars: 38%
- Any licence/constraints text: 78%; recognised open licence: 20%
- Keywords: 31%; WGS84 extent: 100%
- Linked to a catalogue record: 13%
- Code-like layer titles (before using catalogue names): 56%; junk-flagged: 0%
- **Declares an ISO theme (directly or via INSPIRE/DGU crosswalk): 4%** {'none': 170382, 'theme-field': 6029, 'keyword': 516}
- Publisher type: {'public-body': 176894, 'international': 33}

## Datasets (endpoints grouped)
- **Datasets: 129411** from 176927 endpoints; passing: 42078
- Reachable by more than one protocol: 9549
- Endpoints per dataset: {1: 107541, 2: 12621, 3: 3848, 4: 1176, 5: 1745, 6: 117, 7: 435, 8: 1928}
- Grouping rules used: {'title-extent': 14065, 'ogc-name': 5299, 'arcgis-pair': 2692, 'arcgis-ogc': 230, 'catalogue': 121}
- Role (all / passing): {'data': 129014, 'imagery': 359, 'elevation': 29, 'basemap': 9} / {'data': 41840, 'imagery': 234, 'basemap': 3, 'elevation': 1}
- Capabilities offered: {'render': 90554, 'feature-info': 67371, 'query': 53227, 'download': 45921, 'pixels': 3581, 'tiles': 2209, 'time': 163, 'raster-functions': 32, 'catalog': 31, 'multidimensional': 14}

## Coverage and detail
- Coverage level (from extent): {'local': 95306, 'global': 43639, 'regional': 20170, 'national': 16272, 'unknown': 780, 'continental': 760}
- Extent source: {'declared': 175366, 'measured': 1561}; suspect-extent flags: {'world': 43190, 'shared-default': 28830, 'grid-default': 15}
- Endpoints that allow browser access (CORS): 166261
- Detail estimate source: {'none': 159588, 'display': 12760, 'stated': 4445, 'pixel-size': 79, 'tile-cache': 55}
- Detail level, all layers: {'unknown': 159588, '1:25k': 4853, '1:500k': 4575, '1:100k': 3496, '1:5k': 3409, '1:2M': 963, 'coarser': 43}
- Detail level, passing layers: {'unknown': 42842, '1:500k': 1929, '1:5k': 1213, '1:100k': 1056, '1:25k': 993, '1:2M': 84, 'coarser': 28}

## Liveness (sample, up to 2 layers per service)
- {'unchecked': 172978, 'ok': 2132, 'fail': 1813, 'empty': 4}
- Returns data: 0.54; returns data or valid empty: 0.541

## Quality bar
- **Pass: 48145 layers (27%)**; distinct among passing: 30078
- Score median 68.0; bands {'[40, 50)': 7951, '[50, 60)': 23736, '[60, 70)': 58905, '[70, 80)': 51120, '[80, 101)': 35215}

## Size
- layers.parquet: 24.97 MB for 176927 layers

## Top service errors
- robots.txt disallows: 4732
- HTTP N: 1919
- parse: ParseError: not well-formed (invalid token): line 84,: 616
- TimeoutError: : 277
- parse: ParseError: not well-formed (invalid token): line 1, : 138
- parse: ValueError: exception report: 74
- ClientConnectorDNSError: Cannot connect to host mapserveur.a: 63
- ClientConnectorCertificateError: Cannot connect to host serv: 51

AI-tag agreement is not in this run (needs the API key); it comes next.

## shard-7


Run time 140.7 min; 40471 HTTP requests; 4747 blocked by robots.txt.

## Coverage
- Catalogues harvested: 1/1 (records linking to services: 681441)
- ArcGIS server roots reachable: 15/27
- Services crawled OK: 27377/35381 (skipped for time: 0); by type {'wms': 13441, 'arcgis-mapserver': 2447, 'wfs': 10439, 'arcgis-featureserver': 908, 'wmts': 15, 'arcgis-imageserver': 51, 'arcgis-vectortileserver': 50, 'wcs': 26}
- **Layers found: 170001** ({'wms': 83707, 'wfs': 68492, 'arcgis-mapserver': 15392, 'arcgis-featureserver': 1057, 'wmts': 703, 'wcs': 549, 'arcgis-imageserver': 51, 'arcgis-vectortileserver': 50})
- Distinct title+publisher (rough dedupe): 76762

## Metadata quality
- Abstract of 50+ chars: 39%
- Any licence/constraints text: 80%; recognised open licence: 22%
- Keywords: 29%; WGS84 extent: 99%
- Linked to a catalogue record: 13%
- Code-like layer titles (before using catalogue names): 54%; junk-flagged: 0%
- **Declares an ISO theme (directly or via INSPIRE/DGU crosswalk): 4%** {'none': 163278, 'theme-field': 6212, 'keyword': 511}
- Publisher type: {'public-body': 169977, 'international': 24}

## Datasets (endpoints grouped)
- **Datasets: 125849** from 170001 endpoints; passing: 41819
- Reachable by more than one protocol: 8449
- Endpoints per dataset: {1: 107053, 2: 11621, 3: 1704, 4: 793, 5: 1457, 6: 677, 7: 277, 8: 2267}
- Grouping rules used: {'title-extent': 11886, 'ogc-name': 5857, 'arcgis-pair': 997, 'catalogue': 210, 'arcgis-ogc': 151}
- Role (all / passing): {'data': 125622, 'imagery': 199, 'elevation': 20, 'basemap': 8} / {'data': 41684, 'imagery': 130, 'basemap': 3, 'elevation': 2}
- Capabilities offered: {'render': 90893, 'feature-info': 70121, 'query': 51213, 'download': 41634, 'tiles': 1909, 'pixels': 465, 'time': 360, 'catalog': 12, 'raster-functions': 11}

## Coverage and detail
- Coverage level (from extent): {'local': 94368, 'global': 39432, 'regional': 20416, 'national': 13882, 'unknown': 974, 'continental': 929}
- Extent source: {'declared': 168680, 'measured': 1321}; suspect-extent flags: {'world': 39058, 'shared-default': 32573, 'grid-default': 12}
- Endpoints that allow browser access (CORS): 162213
- Detail estimate source: {'none': 153340, 'display': 12152, 'stated': 4458, 'pixel-size': 51}
- Detail level, all layers: {'unknown': 153340, '1:25k': 4967, '1:500k': 3890, '1:5k': 3760, '1:100k': 3445, '1:2M': 582, 'coarser': 17}
- Detail level, passing layers: {'unknown': 43218, '1:500k': 1782, '1:5k': 1464, '1:100k': 1037, '1:25k': 749, '1:2M': 108, 'coarser': 16}

## Liveness (sample, up to 2 layers per service)
- {'unchecked': 166048, 'ok': 2066, 'fail': 1882, 'empty': 5}
- Returns data: 0.523; returns data or valid empty: 0.524

## Quality bar
- **Pass: 48374 layers (28%)**; distinct among passing: 29899
- Score median 70.0; bands {'[40, 50)': 4124, '[50, 60)': 20523, '[60, 70)': 58765, '[70, 80)': 52912, '[80, 101)': 33677}

## Size
- layers.parquet: 23.11 MB for 170001 layers

## Top service errors
- robots.txt disallows: 4745
- HTTP N: 1865
- parse: ParseError: not well-formed (invalid token): line 84,: 542
- TimeoutError: : 260
- parse: ParseError: not well-formed (invalid token): line 1, : 126
- parse: ValueError: exception report: 86
- ClientConnectorDNSError: Cannot connect to host mapserveur.a: 58
- ClientConnectorCertificateError: Cannot connect to host serv: 46

AI-tag agreement is not in this run (needs the API key); it comes next.

## shard-8


Run time 174.0 min; 43067 HTTP requests; 4804 blocked by robots.txt.

## Coverage
- Catalogues harvested: 1/1 (records linking to services: 681441)
- ArcGIS server roots reachable: 23/34
- Services crawled OK: 28195/36478 (skipped for time: 0); by type {'arcgis-vectortileserver': 54, 'arcgis-mapserver': 3096, 'arcgis-featureserver': 1072, 'wfs': 10525, 'wms': 13321, 'wcs': 32, 'arcgis-imageserver': 80, 'wmts': 15}
- **Layers found: 173557** ({'wms': 83452, 'wfs': 66264, 'arcgis-mapserver': 21405, 'arcgis-featureserver': 1748, 'wcs': 382, 'wmts': 172, 'arcgis-imageserver': 80, 'arcgis-vectortileserver': 54})
- Distinct title+publisher (rough dedupe): 80592

## Metadata quality
- Abstract of 50+ chars: 40%
- Any licence/constraints text: 80%; recognised open licence: 20%
- Keywords: 30%; WGS84 extent: 100%
- Linked to a catalogue record: 13%
- Code-like layer titles (before using catalogue names): 52%; junk-flagged: 0%
- **Declares an ISO theme (directly or via INSPIRE/DGU crosswalk): 4%** {'none': 165929, 'theme-field': 6125, 'keyword': 1503}
- Publisher type: {'public-body': 173524, 'international': 33}

## Datasets (endpoints grouped)
- **Datasets: 129035** from 173557 endpoints; passing: 44626
- Reachable by more than one protocol: 9640
- Endpoints per dataset: {1: 108182, 2: 13298, 3: 2269, 4: 1676, 5: 635, 6: 534, 7: 639, 8: 1802}
- Grouping rules used: {'title-extent': 12757, 'ogc-name': 6548, 'arcgis-pair': 1640, 'arcgis-ogc': 194, 'catalogue': 122}
- Role (all / passing): {'data': 128650, 'imagery': 353, 'elevation': 22, 'basemap': 10} / {'data': 44489, 'imagery': 124, 'elevation': 8, 'basemap': 5}
- Capabilities offered: {'render': 95380, 'feature-info': 70087, 'query': 54729, 'download': 41692, 'tiles': 1524, 'pixels': 382, 'time': 95, 'catalog': 41, 'raster-functions': 35, 'multidimensional': 1}

## Coverage and detail
- Coverage level (from extent): {'local': 95677, 'global': 38644, 'regional': 22491, 'national': 15016, 'continental': 871, 'unknown': 858}
- Extent source: {'declared': 171726, 'measured': 1831}; suspect-extent flags: {'world': 38032, 'shared-default': 31887, 'grid-default': 9}
- Endpoints that allow browser access (CORS): 164602
- Detail estimate source: {'none': 156032, 'display': 12565, 'stated': 4880, 'pixel-size': 80}
- Detail level, all layers: {'unknown': 156032, '1:25k': 5231, '1:500k': 4205, '1:5k': 3672, '1:100k': 3552, 'coarser': 435, '1:2M': 430}
- Detail level, passing layers: {'unknown': 45767, '1:500k': 1976, '1:5k': 1280, '1:25k': 1017, '1:100k': 990, '1:2M': 68, 'coarser': 22}

## Liveness (sample, up to 2 layers per service)
- {'unchecked': 169600, 'ok': 2107, 'fail': 1845, 'empty': 5}
- Returns data: 0.532; returns data or valid empty: 0.534

## Quality bar
- **Pass: 51120 layers (30%)**; distinct among passing: 32177
- Score median 70.0; bands {'[40, 50)': 4469, '[50, 60)': 21873, '[60, 70)': 58011, '[70, 80)': 52972, '[80, 101)': 36232}

## Size
- layers.parquet: 24.86 MB for 173557 layers

## Top service errors
- robots.txt disallows: 4801
- HTTP N: 1985
- parse: ParseError: not well-formed (invalid token): line 84,: 615
- TimeoutError: : 279
- parse: ParseError: not well-formed (invalid token): line 1, : 113
- parse: ValueError: exception report: 73
- ClientConnectorDNSError: Cannot connect to host mapserveur.a: 63
- ClientConnectorCertificateError: Cannot connect to host serv: 41

AI-tag agreement is not in this run (needs the API key); it comes next.

## shard-9


Run time 174.1 min; 47615 HTTP requests; 4764 blocked by robots.txt.

## Coverage
- Catalogues harvested: 1/1 (records linking to services: 681441)
- ArcGIS server roots reachable: 20/33
- Services crawled OK: 30397/38575 (skipped for time: 0); by type {'arcgis-imageserver': 165, 'arcgis-mapserver': 4253, 'wfs': 10486, 'wms': 13484, 'arcgis-featureserver': 1917, 'wcs': 25, 'arcgis-vectortileserver': 54, 'wmts': 13}
- **Layers found: 178698** ({'wms': 88213, 'wfs': 64435, 'arcgis-mapserver': 22320, 'arcgis-featureserver': 2586, 'wcs': 747, 'wmts': 178, 'arcgis-imageserver': 165, 'arcgis-vectortileserver': 54})
- Distinct title+publisher (rough dedupe): 81496

## Metadata quality
- Abstract of 50+ chars: 40%
- Any licence/constraints text: 79%; recognised open licence: 20%
- Keywords: 32%; WGS84 extent: 100%
- Linked to a catalogue record: 13%
- Code-like layer titles (before using catalogue names): 53%; junk-flagged: 0%
- **Declares an ISO theme (directly or via INSPIRE/DGU crosswalk): 4%** {'none': 171978, 'theme-field': 6117, 'keyword': 603}
- Publisher type: {'public-body': 178666, 'international': 32}

## Datasets (endpoints grouped)
- **Datasets: 133568** from 178698 endpoints; passing: 45005
- Reachable by more than one protocol: 9116
- Endpoints per dataset: {1: 113964, 2: 11847, 3: 1882, 4: 1145, 5: 1733, 6: 683, 7: 461, 8: 1853}
- Grouping rules used: {'title-extent': 12402, 'ogc-name': 5299, 'arcgis-pair': 2027, 'arcgis-ogc': 261, 'catalogue': 123}
- Role (all / passing): {'data': 133195, 'imagery': 335, 'elevation': 34, 'basemap': 4} / {'data': 44869, 'imagery': 120, 'elevation': 13, 'basemap': 3}
- Capabilities offered: {'render': 99804, 'feature-info': 74004, 'query': 52842, 'download': 40698, 'tiles': 2308, 'time': 1179, 'pixels': 719, 'catalog': 19, 'raster-functions': 15, 'multidimensional': 1}

## Coverage and detail
- Coverage level (from extent): {'local': 97977, 'global': 37651, 'regional': 22776, 'national': 16420, 'continental': 3016, 'unknown': 858}
- Extent source: {'declared': 176385, 'measured': 2313}; suspect-extent flags: {'world': 37178, 'shared-default': 34637, 'grid-default': 32}
- Endpoints that allow browser access (CORS): 170586
- Detail estimate source: {'none': 159131, 'display': 14962, 'stated': 4387, 'pixel-size': 163, 'tile-cache': 55}
- Detail level, all layers: {'unknown': 159131, '1:25k': 5933, '1:500k': 4774, '1:100k': 3798, '1:5k': 3773, '1:2M': 1165, 'coarser': 124}
- Detail level, passing layers: {'unknown': 46605, '1:500k': 2174, '1:5k': 1315, '1:100k': 1215, '1:25k': 1191, '1:2M': 216, 'coarser': 8}

## Liveness (sample, up to 2 layers per service)
- {'unchecked': 174751, 'ok': 2232, 'fail': 1711, 'empty': 4}
- Returns data: 0.565; returns data or valid empty: 0.567

## Quality bar
- **Pass: 52724 layers (30%)**; distinct among passing: 32029
- Score median 70.0; bands {'[40, 50)': 4853, '[50, 60)': 20798, '[60, 70)': 62652, '[70, 80)': 55172, '[80, 101)': 35223}

## Size
- layers.parquet: 25.59 MB for 178698 layers

## Top service errors
- robots.txt disallows: 4762
- HTTP N: 2001
- parse: ParseError: not well-formed (invalid token): line 84,: 586
- TimeoutError: : 250
- parse: ParseError: not well-formed (invalid token): line 1, : 131
- parse: ValueError: exception report: 66
- ClientConnectorCertificateError: Cannot connect to host serv: 54
- ClientConnectorDNSError: Cannot connect to host mapserveur.a: 45

AI-tag agreement is not in this run (needs the API key); it comes next.
