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
  - The extraction tracker's dataset id changes with this (its record is regenerated). Field names are unchanged.

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
