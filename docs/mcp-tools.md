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
