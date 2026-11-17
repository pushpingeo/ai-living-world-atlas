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

- (17 Nov, parked by Rob) A nightly name index of named features (licence blocks, fields, protected areas,
  wind leases) so a named search is one query. Needs a licence check before any building.
