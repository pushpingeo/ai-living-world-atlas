# Liveness sweep 2026-11-28

- Services checked today: 19,651 of 19,651 due (161.2 min, 46,784 requests)
- Service results today: ok 18,829, fail 807, robots 15
- Endpoints checked today: 58,562: ok 55,567, host-down 995, fail 962, missing 916, unmatched 76, robots 46
- Second look (slow retry of failed services): 23 of 705 answered

- Published endpoints: 577,982; checked at least once: 577,966 (100%)
- **Resolving at last check: 97.9%** of checked endpoints that aren't retired (target 98%)
- By protocol: api 100.0%, arcgis-featureserver 96.3%, arcgis-imageserver 98.1%, arcgis-mapserver 97.1%, arcgis-vectortileserver 98.9%, cloud 100.0%, download 85.7%, geojson 100.0%, landing 95.7%, ogc-api-features 100.0%, opendap 0.0%, wcs 98.5%, wfs 98.8%, wms 98.3%, wmts 99.2%
- Data checks on record (one sampled layer per service per visit): ok 242,174, unchecked 7,640, fail 5,686, empty 959
- Retired: 0 endpoints (0 today); revived today: 0
- Failing but not yet retired: 11,818
- Hosts down today (80%+ of 20+ services failed): bio.discomap.eea.europa.eu, climate.discomap.eea.europa.eu, copernicus.discomap.eea.europa.eu, gh.space.gov.rw, gis.dot.nv.gov, gis.georgetown.org, gisweb.cityoflivermore.net, image.discomap.eea.europa.eu, land.discomap.eea.europa.eu, maps.monroecounty.gov, water.discomap.eea.europa.eu
- Publisher text changes today: 20 datasets. 20 sent for re-tagging (~$0.00).

## Hosts with most failing endpoints

- inspire.govconnect.de: 2,220
- services2.arcgis.com: 1,261
- dados.gov.pt: 658
- land.discomap.eea.europa.eu: 403
- image.discomap.eea.europa.eu: 390
- mdi.niedersachsen.de: 374
- vector.sitg.ge.ch: 345
- climate.discomap.eea.europa.eu: 304
- datacarto.karugeo.fr: 296
- idecyl.jcyl.es: 294
- gh.space.gov.rw: 275
- gis.georgetown.org: 274
- water.discomap.eea.europa.eu: 258
- geopau.gov.tn: 249
- buergergis.pforzheim.de: 222

Rules: resolving services rechecked every 7 days, failing every 3, retired every 28. Retired after 3 failed
checks over 14+ days (30 when the whole host was down). Robots.txt refusals are not failures.

## Hosted OpenStreetMap copy

- Lifecycle rules on atlas-data: 2
  - `Default Multipart Abort Rule`: prefix `(whole bucket)`, abort incomplete multipart uploads, enabled
  - `osm-old-releases`: prefix `osm/20`, delete after 30 days, enabled
- uk: release 2026-11-26, manifest 2 days old, oldest release pointed to 2026-11-26 (2 days)
- nl: release 2026-11-27, manifest 1 days old, oldest release pointed to 2026-11-27 (1 days)
- au: no manifest
- us: no manifest
