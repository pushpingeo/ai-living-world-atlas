# What Tobler relies on (the MCP contract)

Tobler (github.com/pushpingeo/tobler) uses the atlas through the MCP server at
`https://atlas-mcp.robdunfey.workers.dev/mcp`, reached from Tobler's own Worker by a service binding.
The Tobler and atlas chats work separately, so this page is the agreement between them: the atlas chat
keeps everything listed here working, and changes or removes any of it only after a note under
"Requests and changes" below. New, optional parameters can be added freely.

## Tools and fields Tobler uses

**`find_datasets`**
- Inputs: `lon`, `lat`, `radius_km` or `bbox` [w, s, e, n]; `concept` (vocabulary id); `capability: "query"`;
  `geometry` (`point` | `line` | `polygon`; datasets with unknown geometry are kept); `limit` (Tobler asks for 100).
- Behaviour: national publishers' datasets are left out when their country doesn't touch the area
  (`include_other_countries` widens it). Tobler depends on this to keep foreign layers out.
- Outputs read per result: `id`, `title`, `publisher`, `publisher_type`, `coverage`, `licence`,
  `extent_may_be_overstated`, `geometry` (list), `country`. Top level: `matches`, `results`.

**`fetch_features`**
- Inputs: `id`; `lon`, `lat`, `radius_km` or `bbox`; `limit` (50–100); `text` (name-like fields, server-side on
  ArcGIS, filtered after fetching on others).
- Outputs read: `returned`, `features` (GeoJSON in WGS84 with properties).
- WFS requests must keep giving the bbox in CRS84 (fixed 17 Nov; without it, layers in a national grid came back empty).

**`vocabulary`**: used by diagnostics only.

Concept ids Tobler maps to (in `js/atlasfeatures.js`): power-plant, mineral-extraction, oil-gas, port-airport,
settlement, school, health-facility, greenspace, tourism-recreation, road, rail, river, pipeline, power-line,
protected-area, heritage-site, admin-boundary, maritime-boundary, offshore-wind-site, renewable-potential.
Renaming or removing one of these breaks a Tobler search.

## Requests and changes

Newest first. Tobler's chat adds requests here; the atlas chat marks them done or declined.

- (20 Nov, Tobler request, **in progress**) **Land elevation at a point, national and global.** All additive; builds
  on `sample` from the depth request below.
  - **New `details.sample.method` values:** `api` (a point-height service: `sample_url` plus `value_path`, a JSON
    pointer such as `/elevations/0`) and `cog` (a cloud-optimised GeoTIFF: `use.file_url` names the file for a point,
    `details.sample.how` says how to fill it, then read the pixel). `identify` can now also be a MapServer identify
    (Geoscience Australia), with `value_path` saying where the number is.
  - **Any `sample` may carry its own templates** (`sample_url`, `file_url`). Placeholders the caller fills:
    `{lon}` `{lat}` and `{west}` `{south}` `{east}` `{north}` (WGS84, box half-size `box_deg`, default 0.001);
    `{x}` `{y}` and `{xmin}` `{ymin}` `{xmax}` `{ymax}` in `sample.crs` (box half-size `box_m`). Some services need
    a national grid (Swiss LV95, Dutch RD, UTM): the `crs` says which.
  - **`sample.browser: false`** marks a source a web page can't read directly (no CORS): fetch through a server.
  - **New records** (concept `elevation`): Scotland's 50 cm national lidar (COG) and one record per Scottish lidar
    survey (18, WMS feature-info); Copernicus GLO-30
    (COG on AWS, surface model, server-side only); France (IGN API), Japan (GSI API), Switzerland (swisstopo API),
    Spain (IGN 5 m WCS), Norway (Kartverket WCS), North Rhine-Westphalia (1 m WCS), Canada (NRCan HRDEM WCS),
    Netherlands (AHN feature-info), Australia (GA 5 m lidar and 1 second, MapServer identify).
  - **England's EA lidar WMS** and **Scotland's lidar WMS** layers now have `sample` (feature-info, metres).
  - Records whose host refuses GitHub's runners (Geoscience Australia) are checked by hand and show `unchecked`.

- (19 Nov, Tobler request, **done**, live 20 Nov) **Values at a point: water depth and shipping density.** All additive.
  - **New capability `sample`**: the endpoint returns a number at a point, not a picture. `find_datasets` takes
    `capability: "sample"`. Picture-only services and vertically exaggerated ones (titles with 3.5x, 5x, 10x,
    "exaggeration", hillshade, colour ramps) never get it.
  - **`get_dataset` endpoints gain `details.sample`**, which says how to read the value:
    `method` (`identify`: ArcGIS ImageServer identify/getSamples; `feature-info`: WMS GetFeatureInfo as JSON, value
    in `field`; `opendap`: one grid cell by index; `lerc-tile`: ArcGIS tiled imagery, read the pixel from a LERC2D
    tile; `wcs`: GetCoverage of a tiny box, GeoTIFF), plus `value` (what the number is: `elevation`, `depth`,
    `density`, `class`, `measure`), `units` and `vertical_datum` where known. For `opendap` and `lerc-tile` it also
    gives the grid (origin, cell size, level) so the cell can be worked out. `use.sample_url` is a ready template
    with `{lon}` and `{lat}` (WGS84) for `identify` and `feature-info`.
  - **`get_dataset` gains `attribution`** (the publisher's attribution or citation line, verbatim) and **`terms`**
    (the publisher's terms of use, verbatim) where recorded. Both are omitted when we haven't recorded them.
  - **New records** (wave `spike-values`, concept `bathymetry` or `shipping`): GEBCO_2026 grid by OPeNDAP from CEDA
    (GEBCO's own distributor); GEBCO_2026 and its type-identifier grid as ImageServers at UNH CCOM; NOAA NCEI's DEM
    Global Mosaic; the World Bank/IMF Global Shipping Traffic Density (all vessels and five types, Esri-hosted tiles,
    CC BY 4.0).
  - **Licence fix:** EMODnet Bathymetry layers (ows.emodnet-bathymetry.eu) and EMODnet's vessel density coverages
    now carry CC BY 4.0 from EMODnet's terms, with EMODnet's attribution line. `open_licence` becomes true.
  - Ids already in the atlas don't change.
  - Live check (mcp-check, 20 Nov), values read through the server's own `sample_url`: off the Niger Delta (4.0N
    5.5E) GEBCO_2026 OPeNDAP -83 m (`dae2320fae0b26f0`), UNH image service -87 m (`9e5419ff6f330200`), NOAA mosaic
    -80 m (`962c2706d519ddd4`), GEBCO TID 40 (predicted, not measured; `77444d56f4682135`). Central North Sea: EMODnet
    DTM -87 m. Esri's own `gebco` copy said -140.5 m off the Niger Delta: prefer the GEBCO records. Shipping density
    ids: all vessels `a337942943e725dd`, commercial `2340ba1f3edf4c6d`, fishing `7ff33a9404410501`, oil and gas
    `7b04932bbcfb62ac`, passenger `11baa92a9a648e32`, leisure `26a0e614508f04e6`.
  - Watch `details.sample.value`: EMODnet's DTM 2016 and 2018 layers give depth as a positive number (`value:
    depth`); everything else in metres is `elevation`, negative below the datum.
  - Curated records' extents are set by hand, so they aren't flagged as overstated: `get_dataset` may show
    `extent_source: "curated"` (new value beside `declared` and `measured`).
  - A curated record whose host refuses crawlers in robots.txt (CEDA, Esri's tiled image services) shows its check
    as `unchecked`, not `fail`: we don't run automated checks there, and the record was checked by hand.

- (18 Nov, atlas change, **planned**, not yet live) **Publisher registry and trusted publishers**
  (`docs/publisher-registry-design.md`). When it ships, all additive except one:
  - `find_datasets` and `get_dataset` gain `publisher_id` (when matched), `trusted` (true/false) and, for data a
    partner hosts, `hosted_by` (e.g. Ordnance Survey data hosted by Esri UK). `find_datasets` gains `trusted_only`;
    trusted datasets get a small ranking boost.
  - **Changed text:** `publisher` shows the registry name when matched ("British Geological Survey" rather than
    "British Geological Survey (BGS)"); `get_dataset` keeps the crawled credit as `publisher_credit`.
  - New D1 columns, so one full reload (search keeps working during it).

- (18 Nov, atlas change, deployed ~14:38 UTC) **Spatial index for `find_datasets`.** Area and concept searches now read a quadtree cell
  key table instead of scanning the extent indexes: a 5 km search reads ~25k rows rather than ~270k (plus a count of
  as many again), and a concept search reads only that concept's datasets in the area (Gulf of Mexico oil-gas: ~1k
  rather than 264k). Details and measurements in `docs/decisions.md`. No input or output field changes. What can differ:
  - **Ranking sees every match** on area and concept searches, not only the 3,000 nearest in size, so the top results
    can change where an area holds more than 3,000 datasets (a city centre, a country-wide concept).
  - **`matches` is exact** on those searches (up to 20,000; above that `matches_capped`). On a large area without
    text or a concept that holds many datasets (the UK, the US, an ocean), results come from the 60,000 best-scored
    datasets world-wide, as before; `matches` then counts the ones in the area (typically a few thousand, not
    "10,000 capped"), with `matches_capped: true`.
  - `debug: true` reports `rows_read` for the whole search (all queries), plus `index`: `cells`, `rank` or `extent`.
  - `include_other_countries: true` and `text` searches use the same paths as before.

- (18 Nov) **Global Energy Monitor: 18 trackers as hosted datasets** (all CC BY 4.0, stated in each file; citation in
  every `fetch_features` `source`). Oil and gas extraction fields (outlines where mapped), gas pipelines and oil/NGL
  pipelines (routes, simplified to ~100 m), LNG terminals, oil and gas plants, coal plants, coal mines, coal
  terminals, wind, utility-scale solar, hydropower, geothermal, bioenergy, nuclear, iron and steel plants, cement
  plants, chemical plants, iron ore mines. Search with `text` "Global Energy Monitor" or the tracker name, or by
  concept (`pipeline`, `power-plant`, `oil-gas`, `mineral-extraction`, `port-airport`).
  - Hosted files are now **tiles**: the `geojson` endpoint URL ends in `index.json`, and `fetch_features` reads only
    the tiles near the area (all tiles for a `text` search; up to 40 nearest otherwise, with `matched_is_partial`).
  - **Left out:** solar rows sourced from TransitionZero (CC BY-NC 4.0, 18,732 rows); the integrated power tracker
    (repeats the individual trackers and carries the same non-commercial part); the methane emitters tracker (plumes
    are CC BY-NC-SA); coal mine boundaries (no licence stated); ownership, finance and LNG-carrier tables (not maps).
  - The extraction tracker keeps its id (11650fec8b9d8e5f). Field names are unchanged.

- (18 Nov) **Hosted download datasets: new endpoint protocol `geojson`.** Some sources only offer a download (Global
  Energy Monitor's trackers come as an .xlsx by request form). The atlas converts them (`atlas/files.py`) and hosts
  one GeoJSON at `…/data/f/<id>.geojson`; the dataset gets a `geojson` endpoint with `query` and `download`.
  `fetch_features` filters the file by area and `text` like any service, and adds `matched` (total in the area) and
  `source` (publisher, citation, licence, release). `where` isn't supported for these. Additive only. First one: GEM's
  Global Oil and Gas Extraction Tracker, once Rob has the March 2026 file.

- (18 Nov) **Tobler request: text search that holds up world-wide. Done** (deployed 18 Nov). `find_datasets`:
  - **`text`** now uses a full-text index (SQLite FTS5) over the **title, publisher, tags (concepts, ISO themes,
    keywords) and the first 300 characters of the description**. All words must match. Words of 4+ letters match as
    prefixes (`therm` finds thermal), and `"quoted phrases"` match exactly. AND, OR, NOT, NEAR and filler words
    (the, of, in, for) are ignored, and punctuation is dropped. Text that leaves no words is an error. Any area size
    works, up to the whole world.
  - **Large areas without text** (over 25 square degrees, roughly 5° by 5°: a region, a country or bigger): candidates are the
    best-scored datasets in the area rather than every one, so results are a good sample, not exhaustive. Add
    `text` or a `concept` to narrow it.
  - **Ranking:** text searches rank by relevance, then publisher authority (government and international bodies
    before local, academic, aggregators and businesses), then fit. Area searches rank by fit, then authority.
  - **Duplicates folded (new, on by default):** results with the same title and much the same extent (over half of
    the larger extent overlapping) are folded into the best-ranked one, listed in a new **`also_available_from`**
    field (`[{id, publisher, publisher_type}]`, up to 10). `fold_duplicates: false` turns it off.
  - **`matches`** now counts up to 10,000; above that, **`matches_capped: true`** is set. New field **`search`**
    says which path ran: `text`, `area` or `large-area`.
  - All field names Tobler uses are unchanged; the new ones are additive.

- (18 Nov) **Africa published, and national authorities pass without a description.** New wave `spike-africa`
  (8,688 passing datasets) added to `runs/published.txt`. It includes petroleum layers from ONHYM (Morocco), the
  Petroleum Authority of Uganda and ANPG (Angola), plus Mozambique's FNDS and WRI's Forest Atlas. Quality rule change
  (Rob's call): central-government and national public-body layers that answer and aren't junk now pass even with no
  description, and code-like or all-caps titles are tidied ("Petroleum agreements onshore"). Expect thinner
  `abstract` text on these. **A trial for Africa only** (country list in `atlas/quality.py`); other regions are
  unchanged until Rob decides.
  *Not available:* GNPC (Ghana), Kenya's State Department for Petroleum and ANPG's ArcGIS Online services need a login
  token. Additive only; no field changes.

- (17 Nov, night) **Tobler request: trusted global services, key-gated services, Esri copies. Design written, not
  built:** `docs/trusted-services-design.md`. Proposes, all additive: `licence_class` (open, open-inferred, esri-mla,
  restricted, stated, unknown) with `exclude_licence_class`; `trusted` and `trusted_only`; `source` and `copy_of` for
  Living Atlas copies, ranked after the publisher's own service; key-gated services (`access: "key"`, key held by the
  atlas Worker) starting with NASA FIRMS. Suggested order: licence class first. Waiting on Rob for the FIRMS key, the
  trusted list and the non-commercial question.
- (17 Nov, night) **Tobler request: EMODnet as feature services, with licences. Done, published ~22:45.** New wave
  `spike-emodnet` (`vocab/seeds/emodnet.yaml`), first in `runs/published.txt`: WFS and WMS of the EMODnet portals plus
  EMODnet's GeoNetwork (2,134 records). A layer's WFS and WMS on one server are one dataset, and `fetch_features`
  uses the WFS. Catalogue records join layers by server and layer name, so CC-BY 4.0 and descriptions come through.
  Human Activities: 251 passing, 156 fetchable as WFS, 178 with CC-BY 4.0. Examples: Heritage Ship Wrecks
  `ee41a8d58f1fe201`, UKHO worldwide wrecks `d266bb32a493da90` (3 wrecks at Rosebank), Pipelines `bb42a4c5b1c1508f`,
  Offshore Installations `a38e968b2ce8d36a`, Wind Farms (polygons) `f70f5adfc354d387`, Military Areas (polygons)
  `ff292558d2076043`, Dumped Munitions (polygons) `821bb9c912e8e65c`. Heritage Ship Wrecks has nothing east of
  Shetland; that's the data, not a fault.
  - **Ids changed:** the old WMS-only EMODnet records are replaced by these (datasets an earlier wave fully holds are
    dropped at publish). Fields unchanged.
  - **Not covered:** EMODnet Geology's and Physics' own servers refuse crawlers in robots.txt, so we don't crawl them
    directly (some Physics layers come in through catalogue links).
  - **"Prefer WFS over a WMS sibling" in general:** done wherever both are crawled, by the same grouping. Next step:
    probe `/wfs` beside known GeoServer WMS endpoints in future crawls, so siblings are found without seeding.
- (17 Nov, night) **Tobler request: mislabelled NSTA record (`bdb5d0a70436343e`). Done.** It wasn't only a title:
  the crawl had grouped NSTA's live service and its `_removed_` twin under one dataset, because they share a title
  and extent, and the removed one came first. Nine NSTA datasets were like this, including `29a134d61746d7dc`
  (pipeline linear, ED50). At publish time (`atlas/titles.py`), such datasets are now split: the original id keeps the
  live service, and the removed service becomes its own dataset with " – removed" in its title (for example
  `bdb5d0a70436343e` live, `16b89c1506aa0b84` removed; `29a134d61746d7dc` live, `d35c83cc47faa79b` removed). Where
  every endpoint is in a status-named service, the word is added to the title. Words: removed, decommissioned,
  abandoned, proposed, planned, superseded, obsolete, archived, expired, relinquished. **Not "historic"**: in
  service names it mostly means heritage (Historic Environment Scotland, Historic England), so it would mislabel
  live data. Also left out: "former" and "draft". *Contract effect:* new dataset ids appear for the split-off
  parts; existing ids keep working and now point at live data; field names are unchanged.
- (17 Nov, late evening) **Tobler request: `fetch_features` "No dataset with id". Done 21:15** (see the outage note
  below). Guarantee: every id `find_datasets` returns can be opened with `get_dataset` and passed to
  `fetch_features`. The deploy smoke test checks it after every MCP deploy, and `mcp-check` checks it on demand.

- (17 Nov, ~20:13–21:15, atlas fault, fixed) **`get_dataset` and `fetch_features` failed** with "No dataset with id"
  while `find_datasets` kept working. The MCP Worker reads dataset details from the viewer's detail files on GitHub
  Pages, and the viewer's switch to gzipped files (`d/xx.json` to `dz/xxx.json.gz`) moved them. The Worker now reads
  the new files (and the old ones as a fallback). Lesson for the atlas chat: a viewer data layout change is an MCP
  change. `mcp-check` (runs/mcp-check.env) now tests all three tools live.

- (17 Nov, atlas change, approved by Rob) **Inferred licence for US federal works.** For about 5-6k US datasets
  from federal agencies (NOAA, USFS, Census, BLM, USGS, BOEM…) that state no open licence, `licence` becomes
  "US federal government work: public domain in the US (inferred, 17 U.S.C. §105; not stated by the publisher)",
  followed by the publisher's credit line, and `open_licence` becomes true. Skipped when the credit names a
  non-federal party (a university, company, state or county). Field names and types don't change, so nothing
  in Tobler should break. Tobler may want to show "inferred" when it reports a licence: the word is always in the text.

- (17 Nov, parked by Rob) A nightly name index of named features (licence blocks, fields, protected areas,
  wind leases) so a named search is one query. Needs a licence check before any building.
