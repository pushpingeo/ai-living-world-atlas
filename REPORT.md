# Liveness sweep 2026-11-21

- Services checked today: 113 of 113 due (49.7 min, 306 requests)
- Service results today: ok 57, fail 55, robots 1
- Endpoints checked today: 1,906: ok 1,777, fail 107, missing 17, unmatched 3, robots 2
- Second look (slow retry of failed services): 0 of 55 answered

- Published endpoints: 577,318; checked at least once: 570,351 (99%)
- **Resolving at last check: 99.7%** of checked endpoints that aren't retired (target 98%)
- By protocol: api 100.0%, arcgis-featureserver 99.7%, arcgis-imageserver 99.9%, arcgis-mapserver 99.6%, arcgis-vectortileserver 100.0%, cloud 100.0%, download 100.0%, geojson 55.6%, landing 96.4%, opendap 100.0%, wcs 100.0%, wfs 99.9%, wms 99.6%, wmts 99.9%
- Data checks on record (one sampled layer per service per visit): ok 143,117, unchecked 6,307, fail 4,841, empty 695
- Retired: 0 endpoints (0 today); revived today: 0
- Failing but not yet retired: 1,735
- Hosts down today (80%+ of 20+ services failed): none
- Publisher text changes today: 0 datasets. 

## Hosts with most failing endpoints

- ows.emodnet-seabedhabitats.eu: 306
- dados.gov.pt: 167
- gisweb.cityoflivermore.net: 92
- terramapas.icv.gva.es: 85
- maps.duesseldorf.de: 81
- buergergis.pforzheim.de: 81
- www45.swfwmd.state.fl.us: 75
- geoportale.regione.lazio.it: 75
- geopau.gov.tn: 72
- gis.dubuquecounty.us: 57
- gisccapps.charlestoncounty.org: 49
- maps.garfield-county.com: 41
- gisservices.zwolle.nl: 37
- gis.dot.nv.gov: 36
- georisques.gouv.fr: 35

Rules: resolving services rechecked every 7 days, failing every 3, retired every 28. Retired after 3 failed
checks over 14+ days (30 when the whole host was down). Robots.txt refusals are not failures.
