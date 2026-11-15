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
