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
