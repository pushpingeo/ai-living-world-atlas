# Decisions

Judgment calls made while building, newest at the bottom. Any of these can be overruled.

## 2026-11-15: Initial build

**Scope: a harvested index, not a hand-curated list.** Quality filtering does the curation. The original 30–50 hand-picked services design is dropped.

**Seeds from the Dateno registry.** About 43.6k catalogues, CC BY 4.0, with software type, owner type and API endpoints. Attribution goes in the README and in the published data.

**The unit is the layer.** One row per ArcGIS layer, WMS layer or WFS feature type. Merging the same data published several ways (FeatureServer + MapServer + WMS + portal record) into one dataset comes later. The spike measures how much duplication there is.

**ArcGIS Online hosted services only come in through a public catalogue.** We never list a whole `services.arcgis.com` organisation, which is where the test layers and personal content live. A self-hosted ArcGIS Server found through a catalogue link gets its whole directory walked, because it belongs to that body.

**Hub feeds use `/api/feed/dcat-us/1.1.json`**, not `/data.json`, which returned broken output on several sites.

**Trust score (0–100).**
- Authority, up to 30: owner type from the registry. Where that's unknown, government or academic domain rules.
- Metadata, up to 40: a real title, an abstract, keywords, licence text, a usable extent.
- Liveness, up to 20: the service responds, and the sample layer returns data.
- Licence clarity, up to 10: a recognised open licence, or at least some stated terms.

A layer **passes** at 60 or more, with no junk flags, a failed check not recorded, and an abstract of 50+ characters. The abstract rule is deliberate: a layer with no description can't be found or trusted, whatever else it has.

**Titles.** If a layer's own name looks like code (`ADP_AVL_Greenbelt_Revised`) and a catalogue record names it properly, the catalogue title is used for display and scoring. The raw name is kept.

**Junk flags look at the title only**, not the service name. Hosted "_view" services are the normal, correct way to publish on ArcGIS Online, so they shouldn't count against a layer.

**Liveness checks.** Feature layers get a `returnCountOnly` query. Map and image layers get a 64×64 image request. Cache-only tile services get one tile at the layer's centre, and a missing tile counts as "unchecked", not failed. WMS gets a small GetMap; WFS gets one feature. The spike samples up to 2 layers per service. The full index will spread checks over a month.

**Themes.** The backbone is the 19 ISO 19115 topic categories. INSPIRE's 34 themes and data.gov.uk's themes are crosswalked to them (see `vocab/themes.yaml`). "Declared" means the source stated it, either as a theme field or as an exact keyword match. AI tagging comes later and is recorded separately.

**Country is the seed catalogue's country for now.** Some UK catalogues publish data for other countries (WorldPop, for example). Deriving coverage from the extent comes later.

**Crawl etiquette.** A named user agent, 2 concurrent requests per host, robots.txt respected, one retry with backoff on 429/5xx.

## 2026-11-15: Coverage and detail (for global-to-local drill-down)

**Two axes, kept separate.** *Coverage* is how much of the world a layer spans. *Detail* is how fine the data is. They vary independently: ESA WorldCover is global at 10 m, and a council layer can be local but crude. Detail levels are named by map scale (`1:5k`, `1:25k`, `1:100k`, `1:500k`, `1:2M`, `coarser`), never by geography, so the two can't be confused.

**Coverage v1** comes from the size of the WGS84 extent: local, regional, national, continental or global. v2 will place each layer in an admin hierarchy (country > region > district, from geoBoundaries), so an agent can ask for "everything covering West Lothian, from global down to local".

**Detail** is an approximate ground resolution in metres, taken from the strongest signal available. The source is recorded in `detail_source`:
1. `pixel-size`: the raster cell size reported by the service.
2. `stated`: a scale or resolution written by the publisher ("1:10,000", "25 m grid", "10K").
3. `tile-cache`: only when the cache stops early (1:20,000 or coarser). Caches routinely go down to about 1:1,000 whatever the data, so a deep cache tells us nothing.
4. `display`: only when the publisher hides the layer until you zoom in past 1:1,000,000 or closer. "Visible at all scales" is a styling default and tells us nothing.

Scale denominators become metres by the usual rule, resolution ≈ denominator / 2000 (0.5 mm on the map).

Early local test: about 14% of layers get an estimate from these signals. Next sources to add, in order:
- ISO/INSPIRE metadata records (spatial resolution is mandatory in INSPIRE metadata, so UK and EU data should do well).
- Feature density from the counts the health checks already return.
- An AI reading of the description, recorded as `detail_source: ai`.

## 2026-11-15: Datasets, endpoints, imagery and tiles

**Record model: DCAT-style.** A *dataset* is listed once, with a list of *endpoints* (DCAT's distributions). This is the most machine-readable common ground: Esri's item fields, CKAN and Hub feeds all map onto it, and imagery will also be exported as STAC. INSPIRE metadata is used where it exists, but only as one signal, because implementations are often poor.

**Each endpoint states what it can do**, in verbs that mean the same across ArcGIS and OGC:
- `query`: filter features.
- `download`: bulk export.
- `render`: draw a map image.
- `tiles`: pre-cut tiles.
- `feature-info`: click to identify on a WMS.
- `pixels`: raster values.
- `catalog`: a mosaic of many images.
- `raster-functions`, `time`, `multidimensional`.

Protocol specifics go in `endpoint_info`: max records, paging, output formats, image formats, bands, pixel type, tiling scheme, zoom range and tile URL template.

**Grouping endpoints into datasets.** Strong rules:
- `arcgis-pair`: MapServer/N + FeatureServer/N of the same service.
- `arcgis-ogc`: an ArcGIS service's own WMS/WFS, matched on title. ArcGIS WMS numbers its layers differently from REST, so matching by id was wrong and produced a 54-layer blob.
- `ogc-name`: the same layer name on one OGC server.
- `catalogue`: one catalogue record, same layer title.

Weak rule: `title-extent`, meaning same title and publisher with extents overlapping by 80% or more. Title-based rules ignore numeric or one-word titles and stop at 8 endpoints, because past that they snowball. The rule that joined each endpoint is recorded.

**Imagery and tiles in scope.** ImageServer captures bands, pixel type, data type, mosaic, raster functions, download rights and multidimensional support. WMTS and WCS are now crawled. Each dataset gets a role (`data`, `imagery`, `elevation` or `basemap`) from the service shape plus words in the title. Basemaps keep what you need to use one: whether the tiles are Web Mercator standard, the zoom range, the format and a tile URL template. WMTS and WCS liveness checks aren't written yet; those layers show as "unchecked".

## 2026-11-15: Publisher attribution and demo data (after UK run 4)

**Hubs list other people's services.** A Rivers Trust Hub linking EEA image services made the Rivers Trust look like the publisher. Now, when a Hub links a service on a non-ArcGIS-Online host, the Hub's owner goes in `listed_by`, not `publisher`. The publisher then comes from the service itself, or failing that the host name. Hubs linking another organisation's ArcGIS Online services are still attributed to the Hub owner; that needs an organisation-ID check later.

**GeoServer sample data is flagged** (`demo-data`): the `topp:`, `sf:`, `tiger:` and `nurc:` namespaces, plus layers such as Spearfish and the North America sample imagery. Several council and university GeoServers still publish the install defaults.

## 2026-11-15: AI tagging test, and a catalogue-join bug it exposed

**Tagging test** (`docs/evals/tagging-gb-2026-11-15.md`): Haiku 5.5 and Opus 5.5 each tagged the same 200 passing UK datasets, constrained to the fixed vocabularies.
- They chose the same first ISO theme 86% of the time and the same first concept 84% of the time.
- Both matched the publisher's own declared theme 85% of the time.
- Most disagreements are ordering (land-cover vs agriculture first) or genuinely ambiguous layers.
- **Decision: Haiku does the tagging at scale.** Batch cost is about $23 per 100k datasets. Opus is used only for evaluation.
- Opus 5.5 refuses a forced tool call, so for Opus the tool is requested in the prompt instead.

**Bug found by the test.** A catalogue record linking one layer of an ArcGIS service (e.g. Bristol's recycling points) was lending its description to every layer in that service. Haiku spotted the contradiction and lowered its confidence; we were the ones in the wrong. Records now attach only if they link that exact layer, or they link the whole service and either the titles match or the service has 3 layers or fewer. This will lower the "usable description" and pass figures somewhat, and make them honest.

**Proposed concepts to review:** the models suggested hydrogeology, historic-map, airborne-geophysics, seismic-survey, nitrate-vulnerable-zone, traffic-count, compulsory-purchase-order and fly-tipping, among others. They go into the vocabulary when they recur across countries, not on one UK run.

## 2026-11-15: False extents

Extents are often much bigger than the data. In the UK run:
- 6% of layers in services with 3+ layers just copy the service extent.
- 8% of council layers claim a national-or-larger extent; 183 of those are exactly the whole-GB grid.
- 1,400 layers claim the whole world.

**Now:** every layer is checked against four rules (`shared-default`, `world`, `grid-default`, `too-big-local`). Suspect ArcGIS feature and map layers are measured with `query?returnExtentOnly=true`: one request each, capped at 15k a run. The declared extent is kept in `declared_bbox`, and `extent_source` says `measured` or `declared`. In a local test, 1 in 5 measured layers turned out less than half the size they claimed. The viewer halves the ranking of suspect extents it couldn't measure, and says so in the details.

**Later:**
- WMS/ImageServer: render one small image over the claimed extent and take the bounds of the non-empty pixels.
- Real footprints: a coarse grid of where features actually are, so a "UK" layer covering three counties shows as three counties.
- Comparing council layers with the council's own boundary, once the admin hierarchy exists.

## 2026-11-16: D1 write limit

Cloudflare's free tier allows 100k row writes a day in D1, and index updates count too. Each full reload of the ~40k-row database cost more than that, and three reloads on 15–16 Nov hit the limit. Reads were unaffected. The deploy now keeps a hash of every row it loaded (`rows.json` on `results/mcp-deploy`) and writes only the difference. An unchanged rebuild writes nothing; a normal recrawl should write a few thousand rows. A crawl that changes every row (a schema change, say) still needs a full day's allowance, so those should be spaced out, or moved to the $5/month Workers plan if they become routine.

## 2026-11-16: Going global in waves

**Global backbones** are hand-picked in `vocab/seeds/global.yaml`: UNEP-WCMC, GEBCO, ESA WorldCover (Terrascope), JRC/GHSL, FAO, SoilGrids, Marine Regions, Global Forest Watch, NASA GIBS, the EEA servers, and public Living Atlas items. Living Atlas items needing a subscription or credits are skipped; each item's credits become its publisher.

**Download-only sources are in.** GHSL, Copernicus DEM, Overture, HydroSHEDS, GEM, geoBoundaries, Natural Earth, the UNESCO list, the USGS earthquake feed and Overpass have no map service to crawl. They are listed as records (`download`, `cloud`, `api` or `landing` endpoints) with their own metadata, checked with a plain GET. Leaving them out would leave holes exactly where national data is thin.

**INSPIRE** comes through the geoportal's GeoNetwork search API, not CSW XML. It is easier to page and returns ISO topic categories, INSPIRE themes and the stated scale. A stated scale becomes `detail_source: metadata`, which should lift detail coverage a lot for EU data. Every shard harvests the catalogue, then crawls only its share of the services.

**Waves** are run files in `runs/` (name, countries, seed files, shards). Shards run in parallel in Actions and merge into one `results/spike-<name>` branch: US 16 shards, INSPIRE 8, global 4, Canada/Australia/NZ 4. `runs/published.txt` lists which waves the viewer and MCP server use. The US and INSPIRE join once the viewer loads its index in tiles, because one file for every dataset won't hold at that size.

**Tagging** runs per wave and skips anything already tagged. Costs are reported per wave.

## 2026-11-16 — Europe via data.europa.eu, not the INSPIRE geoportal
The INSPIRE geoportal stopped resolving (DNS failure from GitHub runners; its record URLs 302 to data.europa.eu).
data.europa.eu harvests the national INSPIRE catalogues and exposes one search API: about 516k datasets with a
WMS distribution and 366k with WFS (Nov 2026; gdi-de alone is ~300k). We scroll it once per wave in a separate
harvest job and hand the records to every shard, rather than each shard re-harvesting. Each record's own country
is kept. EU data themes are crosswalked to ISO only where clear (agri, econ, energy, environment, health,
society, transport). Not yet used: the distribution title often carries the WMS/WFS layer name, which would
make the catalogue-to-layer join exact.

## 2026-11-16 — Viewer and MCP carry passing datasets only; big waves merge without regrouping
With the US wave the viewer data reached 974 MB, against GitHub Pages' 1 GB site limit, and Europe will be bigger
than everything else together. The viewer and the MCP server now carry only datasets that pass the quality bar
(141k across UK, global, CANZ, US); the full index, failures included, stays in the wave files on the results
branches. The "passes quality bar" toggle is hidden and the MCP's include_low_quality option removed.
The Europe merge ran the runner out of memory. Very large waves (CONCAT=1) now merge by streaming each shard's
files together without regrouping datasets across shards; the cost is that the same data published on two hosts
that landed in different shards shows up twice.

## 2026-11-16 — Local development plans grouped into one collection per council (Rob's choice)
Of Europe's ~560k passing datasets, ~490k were individual local plans (mostly German Bebauungspläne via
XPlanung/INSPIRE PLU, also Croatian UPU/PPUO and others), each its own service. atlas/collections.py groups each
council's plans (3+) into one dataset, "Development plans – <council>", listing the first 300 plan services as
endpoints (each labelled with the plan name). Members stay in the files with q_pass false and flag in-collection.
Detection: plan wording in title/abstract/licence, plus any service where at least half the datasets read as plans
(the half rule stops national services with one zoning layer, e.g. swisstopo, being swept in). XPlanung's demo
council "Testhausen" is excluded as demo data. Result: 1,672 collections; Europe passing 71.9k. The derived wave is
results/spike-europe (built by the collections workflow from results/spike-inspire).

## 2026-11-16 (night): Search ranking for small areas, from Tobler's place-finding tests

**Size match on a log scale.** `find_datasets` scored every regional or global layer at 0 for a site-sized search, because the plain ratio of search area to layer extent is tiny. Ranking then fell back to quality score, so local layers with inflated extents (Pennsylvania mines, Spanish power plants) came first for sites in Congo and Argentina. Fit is now coverage × the better of the area ratio and a log-scale size match, so a provincial layer beats a continental one, which beats a global one, and none scores 0. Layers flagged with a possibly overstated extent are now multiplied by 0.2 (was 0.5).

**Tool description says what the atlas actually covers** (it still said "United Kingdom (test index)"), so an agent elsewhere doesn't give up before trying.

**Known, not fixed:** some ArcGIS servers advertise Query but refuse it (e.g. Western Michigan's Global Mines MapServer, including the Maus et al. mining polygons). The crawler can't tell without trying a query; the planned liveness sweep should test one query per layer and drop the capability when it fails. The "Global Power Plants Aug24" layers are a third-party summary of GEM's tracker (operating plants only, about 59k), not GEM's full release; newer plants such as Nachtigal (2024) aren't in it.

## 2026-11-17: Rolling liveness sweep
The published index (passing datasets only: 512k endpoints on 181k services, 2,233 hosts) is rechecked nightly by
the `sweep` workflow (atlas/sweep.py). Until now only 6% of published endpoints had ever had a data check, because
the crawl samples two layers per service.
- **Unit of work is a service.** One visit costs what a crawl of it costs: the service JSON and /layers, or one
  GetCapabilities, plus one small data request for one layer, rotating week by week. From that we learn, for
  every published endpoint on it, whether the service resolves, whether the layer is still listed, and whether its
  title or description changed.
- **Schedule.** Resolving services every 7 days, failing ones every 3, retired ones every 28. Up to 45k services a
  night, so the first full pass takes about four nights and then settles at ~26k a night.
- **Retiring.** An endpoint is retired after failing on 3 checks spanning 14+ days. When 80%+ of 20+ services on one
  host fail on the same night, the host is "down" and the window is 30 days, because that can be a block on the
  GitHub runner rather than a dead server. Robots.txt refusals don't count. A retired endpoint that answers again
  comes back. If a service answers but none of its known layer ids match (a parser difference or a restructure),
  it counts as resolving ("unmatched"), not as missing layers.
- **Applied at publish time, not in the wave files.** The wave files stay as crawl snapshots. combine.py drops
  retired endpoints (and datasets left with none), marks endpoints failing but not yet retired with
  `"status":"failing"`, and puts the latest data check in the endpoint's `check`. Check dates are left out of the
  published rows on purpose, so the MCP database only gets writes when something actually changes.
- **Publisher text edits.** When a layer's title or description changes, the dataset's text is replaced only where
  it was that layer's text (a catalogue record's wording is left alone), and that dataset is re-tagged in the same
  run through the Batch API into `results/tags-sweep`. Over 50k changed datasets in one night is treated as a
  parser problem: not re-tagged, flagged in the report.
- **Outputs** on `results/liveness`: state.parquet (one row per endpoint), changes.parquet, REPORT.md, history.csv
  (one line per night, including the resolving rate against the 98% target).

## 2026-11-17: Europe harvest rerun
data.europa.eu's scroll is a server-side cursor, so a bad page can't be asked for again; run 3 lost over half the
WMS and WFS records that way. The harvester now restarts a broken scroll from the top and skips records it already
has, and also restarts when a scroll "finishes" short of the reported total (asking again for a page can move the
cursor past it silently). Page size cap raised to 300 MB so large pages aren't cut. Run 4 uses 20 shards for about
2.4x the records. When a source wave merges, the spike workflow starts the derived collections build; tagging is
still started by hand, and tag_batch refuses to submit more than MAX_DATASETS (default 200k, about $18).

**Text search inside a layer (`fetch_features` `text`).** Tobler needs "the M9" or "Kipoi" from a layer with thousands of features, where the 100-feature cap returns a random handful. For ArcGIS endpoints the worker reads the layer's name-like string fields (cached a day) and adds `UPPER(field) LIKE '%TEXT%'` across them; if the server refuses that, it fetches up to 2,000 features and filters them itself. WFS is filtered after fetching. No new cost beyond one cached layer-description request.

## 2026-11-17: WFS bounding boxes must state their CRS

`fetch_features` (and the viewer) asked WFS servers for `version=1.0.0&srsName=EPSG:4326&bbox=lon,lat,lon,lat`. `srsName` only sets the output; without a CRS on the bbox the server reads it in the layer's native CRS. For NatureScot's SSSI layer (British National Grid) the box landed near the grid origin and returned nothing, so Tobler missed Linlithgow Loch's neighbouring SSSIs. With the CRS stated, the same request returns 10 SSSIs. Now: WFS 1.1.0 with `srsName` and bbox in `urn:ogc:def:crs:OGC:1.3:CRS84` (lon/lat order), falling back to 1.0.0 with `,EPSG:4326` on the bbox; an XML exception report is named as such. Affects every WFS layer not published in WGS84, which is most national ones in Europe. Worth a spot check across a sample of WFS layers.

## 2026-11-17: geometry types and home countries in search
- **Joining parquet parts streams now.** `parts get` writes part by part and can read only some columns; the fetch reads just the layer columns the combine step uses. On GitHub's runners Europe's layers (ten parts of ~50 MB) fitted in memory, but in a 7 GB workspace the join was killed and `actions-fetch.sh` reported it as "no data yet". A skipped wave is now a warning and a line in SOURCES.txt instead.
- **Geometry type in search.** D1 gains `gtypes` (point, line, polygon across a dataset's layers, from the ArcGIS crawl; WFS layers say only "features", so they stay unknown). `find_datasets` returns `geometry` and takes `geometry` to filter (unknowns are kept). Tobler's road search had been spending its budget on junction-point layers.
- **Home country in search.** D1 gains `home`: the publisher's country, blank for international bodies, publishers with no country and the datasets listed in `vocab/extent_overrides.yaml` (USGS MRDS). `find_datasets` leaves out datasets whose home country doesn't touch the area (countries with 3° of waters, from Natural Earth: `vocab/country_areas.geojson`; any European country in the area admits "EUROPE" datasets). `include_other_countries` widens it. A rule that flagged extents lying mostly outside the publisher's country was tried first and dropped: it flagged 27k datasets, many of them small layers inside their own country.
- The new columns change the table layout, so `api_data` now forces a full reload when the layout changes (stored as `__schema__` in rows.json). A full load is about 256k rows plus index writes, well inside Workers Paid.

## 2026-11-17 (evening): liveness sweep, first-week fixes
Two full runs landed on 17 Nov: the push-triggered one at 00:22 UTC and the scheduled one, which GitHub started at
12:07 instead of 03:23. The midday run failed 1,014 endpoints against 162 at night (different services, so not a
clean comparison, but a hint that busy hours matter). A probe of the failures from a runner (round 3 in
`runs/probe.urls`, now with time and size) sorted them into three kinds:
- **Alive but slow.** datamap.gov.wales's WFS GetCapabilities is 3.7 MB and took 47 s; dados.gov.pt's redirects to
  DGT's WFS took 38-56 s. With a 30 s timeout these fail every visit and would be retired from 1 Dec.
- **Busy at the time.** gisweb.cosb.us, EA newt and habitat WMS, gis.olympiawa.gov, Brecon Beacons and Brock
  University (403s, flagged as host down) all answered the probe within 2 s.
- **Really failing.** Rutgers ocean data (60 s, nothing back), gis1.mgipu.hr (Croatia's plan rasters: 502),
  Cook County (404).

Changes:
- **Second look.** At the end of each run, failed services get one more try: one at a time per host, 90 s timeout, up
  to 3,000 services and 40 per host, with the last 20 minutes of the run kept for it (a sixth of the run when it is
  short). Only a success replaces the first result. REPORT.md and history.csv show how many answered.
- **S3 folders.** A "cloud" endpoint that is an S3 prefix (Overture's `/release/`) has no object behind it and
  answers 404, so it would have been retired. It is now checked by listing the prefix.
- **history.csv keeps every run**, with `trigger` (schedule/push) and `started` (UTC), so late scheduled runs show up.
  The first full night's line was overwritten by the midday run before this; its figures are in the handover
  (45k services, 196.6 min, 107,377 requests, 99.6% resolving, 539 failing).

## 2026-11-17 (evening): US federal works counted as open (Rob's call)
US services rarely state a licence (22% have no text, most of the rest are credits), so better wording rules don't
help. Rob approved inferring public domain for US federal agencies' work (17 U.S.C. §105), labelled as inferred in
the licence text and skipped when the credit names a non-federal party. Applied at publish time (`atlas/licences.py`
from combine.py), so the wave files keep what was crawled. 5,420 marked on the US wave; 3,228 in the published index (347 skipped), because datasets also found by an earlier wave keep that wave's publisher type. Noted in
`docs/mcp-tools.md` first; field names and types are unchanged. Details: `docs/us-licences.md`.

## 2026-11-17 (evening): gzipped detail shards in the viewer (Rob approved)
The viewer's detail shards were 628 MB of GitHub Pages' 1 GB limit. They are now gzipped JSON keyed by the first 3
characters of the dataset id (`data/dz/xxx.json.gz`, 4,096 files) and unzipped in the browser with
DecompressionStream; a file that arrives already unzipped is read as it is. `meta.json` carries `detail_dir`,
`detail_key` and `detail_gz`, so the code follows whatever layout the data was built with. The pages build now
version-stamps `app.js` and `style.css`. Site: 702 MB to 203 MB; a detail click fetches ~30 KB instead of ~2.5 MB.

## 2026-11-17 (night): MCP broke for an hour after the viewer change
The MCP Worker reads dataset details from the viewer's detail shards on GitHub Pages. Moving them to gzipped
`dz/` files at ~20:13 broke `get_dataset` and `fetch_features` ("No dataset with id") while `find_datasets` (D1) kept
working; Tobler noticed first. Fixed ~21:15: the Worker reads the new files, with the old layout as a fallback. The
deploy-mcp smoke test now also opens a dataset, and `mcp-check` (runs/mcp-check.env) tests all three tools Tobler
uses. Lesson: a viewer data change is an MCP change and goes through docs/mcp-tools.md first.

## 2026-11-17 (night): Tobler's requests: EMODnet, NSTA status words, trusted services
- **EMODnet wave** (`spike-emodnet`, `vocab/seeds/emodnet.yaml`): every EMODnet portal's WFS and WMS plus EMODnet's
  GeoNetwork (2,134 records). A layer's WFS and WMS on one server group into one dataset (ogc-name). GeoNetwork
  links now keep the layer name, and records join OGC layers by (server, layer name), so the record's licence and
  description reach a layer on a 200-layer server. Human Activities: 251 passing, 156 fetchable as WFS, 178 with
  CC-BY 4.0. The harvester also had to read GeoNetwork codelists returned as objects (it crashed on EMODnet's).
  EMODnet Geology and Physics servers refuse crawlers in robots.txt; we respect that.
- **Publishing order and duplicates:** the focused wave goes first in `runs/published.txt`, and combine drops a
  dataset whose endpoints all belong to an earlier wave's dataset (`drop_covered`). On the existing waves that removed
  2,159 cross-wave duplicates. EMODnet's old WMS-only ids give way to the grouped records' ids (noted in mcp-tools.md).
- **Status words in service names** (`atlas/titles.py`, at publish): live and removed services grouped under one
  title are split (444 across all waves; the original id keeps the live one); 172 titles gained a status word. Not
  "historic", "former" or "draft": in service names those mostly mean heritage, old boundaries or a work folder.
- **Trusted services, key-gated APIs, Esri copies:** design only, `docs/trusted-services-design.md`.

## 2026-11-18 01:00: Africa wave held back
The 01:00 check found what the 22:00 review did: `results/spike-africa` has 17.6k datasets, 3,258 passing, but the
seeded petroleum bodies don't come through. GNPC, Kenya's State Department for Petroleum and ANPG's ArcGIS Online
services answer "Token Required" (listed publicly, not open). ONHYM and the Petroleum Authority of Uganda are open
but fail the quality bar (no descriptions, code-like titles). Not tagged, not published. Waiting on Rob's call on
letting authoritative national sources pass without a description.

## 2026-11-18: national authorities pass without a description (Rob's call); Africa published
Central-government and national public-body layers that answer and carry no junk flags now pass with a total of
45+ even with no description, and code-like or all-caps titles are tidied (`authority_pass` in quality.py). It runs
at scoring and again at merge, so a remerge rescores an old crawl. Local government is excluded. Africa was
remerged (3,258 to 8,688 passing), tagged ($0.76) and published. **Trial, Africa only** (Rob): where data is scarce,
something beats nothing; for the US and Europe it may add noise. Gated by layer country (`AUTHORITY_PASS_COUNTRIES`),
so other regions are unchanged when recrawled. Review Africa's results before extending it.

## 2026-11-18 (early): full-text search, large-area path, safe full reloads
Tobler's world-wide text searches overloaded D1: `LIKE '%x%'` plus a full `COUNT(*)` read every row, and once D1 is
overloaded every query fails for the rest of its 10-second window (one heavy search takes everyone down).
- `ds_fts` (SQLite FTS5) over title, publisher, tags and the first 300 characters of the description. Its rowid comes
  from the dataset id, so incremental loads delete and reinsert entries directly. Query joined with `CROSS JOIN` so
  SQLite reads the matches first (a plain JOIN read ~265k rows per search; now 24 for "VIIRS", 6k for "fire").
- Areas over 25 square degrees without text read candidates best-score-first through `ix_rank` and stop at 3,000.
  Counts stop at 10,000 (`matches_capped`).
- Ranking: relevance, then publisher authority, then fit; duplicates (same title, extents overlapping by more than
  half of the larger) folded into `also_available_from`.
- Full reloads build `datasets_next` and `ds_fts_next` and swap them in at the end (index names carry a per-load
  suffix), so search keeps working through a reload. First run: 264k datasets, 205 MB of SQL, 8 minutes.
- Still heavy (not new): small-area searches read ~270k rows (the extent index narrows one axis only), and a concept
  over a large area reads the whole rank index. Fix: a spatial cell key and a concept table (next).
- `debug: true` on find_datasets adds `rows_read`, for checking these.

## 2026-11-18: download-only datasets hosted by the atlas (GEM first)
GEM's trackers are only available as an .xlsx by request form, and the map files GEM's own maps use move between
releases (March 2026 addresses already 404), so the atlas hosts a copy: CC BY 4.0, stated in the file's About sheet,
allows it with attribution. `atlas/files.py` converts per a spec in `vocab/files/` (outline from WKT where valid and
near the row's point, else the point), writes `files/<id>.geojson` and the record for the `spike-files` wave. New
endpoint protocol `geojson` (query, download); the Worker filters the file by area and text and returns `matched`
and `source`. Raw downloads stay out of git (size); refreshing is: new file, one command, push.

## 2026-11-18 (morning): all of GEM's mappable trackers, as tiles
Rob's download held 34 GEM files. 18 are maps under CC BY 4.0 and are now hosted and searchable. Large outputs (gas
pipelines 68 MB as GeoJSON) can't be read whole per request, so files.py writes gzipped 10° tiles plus an index of
tile extents; the Worker reads only the tiles that touch the area (up to 40 nearest without text; every tile, 12 at
a time, for text). Solar rows marked with a TransitionZero ID are excluded because that source is CC BY-NC; the
rest of the solar tracker is CC BY. Not published: integrated power (repeats the trackers, carries the same NC
part), methane (plumes NC-SA), coal mine boundaries (no licence stated), and the non-spatial tables.

## 2026-11-18 09:00: GitHub dropped the nightly sweep
No scheduled run of the sweep was created for 18 Nov at all (17 Nov's 03:23 slot started at 12:07). GitHub runs
schedules on a best-effort basis, so one nightly slot can't be relied on. The sweep now has four slots (03:23,
09:23, 15:23, 21:23 UTC) and a small `due` job: a scheduled run stops at once if history.csv already has today's
date; a push or manual run always goes ahead. Side effect: a skipped slot still counts as a completed sweep, so
pages and deploy-mcp rebuild after it (harmless: nothing changes, the MCP load writes 0 rows). 18 Nov's sweep was
started by hand at 09:02. If slots keep going missing, the next step is a Cloudflare cron trigger calling GitHub's
workflow_dispatch (needs a GitHub token stored as a Worker secret, which Rob would set).

## 2026-11-18 (afternoon): first sweep with the second look
Started by hand 09:02 (GitHub dropped the 03:23 slot). 45,000 services, 244.5 min, 106,917 requests. Resolving
99.5% (up from 99.3%); 1,723 failing, none retired; no hosts down. Second look: 24 of 106 failed services answered
on the slow retry. Checked at least once: 367,633 of 577,273 endpoints (64%). The 09:23 slot (started 11:57) waited
for the manual run, then skipped as designed.
Fixed: the sweep didn't check atlas-hosted `geojson` endpoints, so GEM showed 0% resolving and would have retired
from early December; it now fetches their index.json. Slow retries stop starting 3 minutes before the deadline
(the run overran by 4.5 min). GEM endpoints keep "failing" status until their next recheck (every 3 days).
Overture's S3 folder isn't due again until 20 Nov, so the listing fix is still unproven.

## 2026-11-18 (evening): spatial index for find_datasets
Area searches filtered on four extent columns, and an index range on one column can't narrow the other three, so a
5 km search read ~270k rows (plus a count query reading as much again), and a concept over a large area read the whole
rank index. A burst of those could overload D1 for its 10-second window and fail every query.

**Quadtree cell keys** (`ds_cell`, built in `atlas/api_data.py`, read by `cellSelect` in the Worker). Lon/lat cells,
360/2^L by 180/2^L degrees, levels 0-18. A dataset sits at the finest level where its extent spans at most 2 x 2 cells
and gets one key per cell, so London (which straddles Greenwich) lands at level 10, not level 1 as a single
"smallest containing cell" would put it. Keys start with the dataset's home country (`GB:0312...`), so a search reads
only the countries it would keep anyway, and are repeated per concept (`c:oil-gas|GB:0312...`), so a concept search
reads only that concept. 264k datasets give 1.88M keys. A search reads exact keys for the levels coarser than the
area and key ranges (prefixes) at the area's own level. Each key row carries the extent rounded outwards to 0.001°,
which drops datasets whose cell meets the area but whose extent doesn't before any lookup.

**Shape of the query, found by measuring on a local D1** (each step was slower than the next):
- UNION of ranges: D1 caps compound SELECTs. A flat chain of ORs: SQLite caps expression depth at 100 (Europe has
  50 countries x 4 ranges). Now a balanced OR tree; areas over more than 8 countries use coarser ranges to keep the
  SQL short (Europe-wide: ~20 KB, D1 allows 100 KB).
- `DISTINCT` on the keys or a plain `pass = 1` on datasets makes SQLite scan a whole index instead; the cell path
  prefixes filters with `+` and lets `id IN (...)` dedupe.
- A window count and a SQL sort cost 3 reads per match. The cell paths now return every match as a slim row
  (id, title, publisher, type, score, extent), rank and fold them all in the Worker, then read full rows for the 100
  kept. Matches are exact, and every match is ranked by fit (before, only the 3,000 nearest in size were).
- `datasets` is now WITHOUT ROWID: a lookup by id is one read, not two.

**Large areas without a concept** are cheap through the cells where the area holds few datasets (Nigeria: 2k) and
costly where it holds many (the US: 90k). The Worker counts the area's keys up to 20,000 first; below that it uses the
cells, above it reads the 60,000 best-scored datasets world-wide from the rank index (which now also holds extent
and home, so no lookups) and keeps those in the area. Areas over 20,000 square degrees skip the count. Those results
are a best-scored sample, as before; `matches` then counts that sample and `matches_capped` is set.

**Results, same local D1, rows read per search** (old: main query only, as mcp-check reported; the old count query
read about as much again):

| Search | Old | New |
|---|---|---|
| Edinburgh 5 km | 271,148 | 25,393 |
| Edinburgh road, query, line | 264,429 | 348 |
| Berlin 10 km | 278,628 | 54,902 |
| Lagos 20 km | 266,145 | 8,043 |
| Shetland pipeline, query | 264,442 | 381 |
| Gulf of Mexico, oil-gas | 264,415 | 1,039 |
| US protected-area | 264,415 | 10,263 |
| Europe admin-boundary | 105,684 | 30,263 |
| Nigeria, no text | 264,415 | 16,956 |
| UK, no text | 35,874 (195k with count) | 84,227 |
| World, no text | 3,000 (13k with count) | 12,200 |

Same match counts on every complete path. A brute-force check over 400 random areas (city to world, poles,
antimeridian, with and without concepts) found 0 missed or extra datasets. Unchanged: text search (FTS) and
`include_other_countries`, which keeps the old extent path.

**Costs.** The SQL for a full reload grows from 205 MB to 338 MB (about 85 pieces, ~8 minutes), the database from
~377 MB to ~660 MB, and peaks near 1.3 GB while a reload builds the new tables beside the old. Fine on Workers Paid
(10 GB, 50M row writes a month; a full reload is ~5M). **Over D1's free-plan 500 MB limit**: switching Workers Paid
off would need a trim first (the id index on ds_cell, 88 MB, only serves incremental deletes; FTS keeps its own copy
of the text, ~126 MB).

## 2026-11-19: ArcGIS layers that can't page (Historic Environment Scotland)
Rob reported HES layers not working. All 10 HES datasets are on inspire.hes.scot (ArcGIS Server 11.5, British
National Grid), served as MapServer, WMS and WFS. The server was fine and the sweep marked them ok, but every
`fetch_features` call failed: the layers say `supportsPagination: false`, and such a layer refuses any query that
includes `resultRecordCount` ("Pagination is not supported."), which `fetch_features` and the viewer's feature preview
always sent. Their WFS offers GML only, which neither can read, so there was no fallback. The sweep's data check
doesn't send that parameter, which is why it said ok.

Fix (generic, not HES-specific): when an ArcGIS query is refused, `fetch_features` and the viewer ask once more
without `resultRecordCount` and cut the result to the limit themselves. Live check: 9 of the 10 HES datasets now
return features (the tenth is WMS only: a picture, no features). mcp-check now covers all 10.
Not tested in a browser: the cloud browser has no WebGL, so the viewer's map can't start there.
