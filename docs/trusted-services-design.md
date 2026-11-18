# Trusted global services, key-gated services and licence classes: design (17 Nov 2026)

Tobler request 3 (docs/atlas-requests.md in the tobler repo). Design only; nothing built. Every change below is
additive to `docs/mcp-tools.md`: new optional inputs and new output fields; no renames.

## What we have today

- The global wave holds 11,443 passing datasets. 9,469 of them come from the public Living Atlas group
  (`publisher_type: curated-collection`). The publisher is read from each item's credits, so many say NOAA, USFS,
  Environment Canada and so on, but the service is Esri's copy.
- 885 passing global datasets say "This work is licensed under the Esri Master License Agreement". Today that's
  plain licence text, so Tobler has to pattern-match it.
- NASA FIRMS is in the atlas only as Esri's copy and an Alaska regional service.

## (d) Licence class: do first, smallest and most useful

A new output field, `licence_class`, on `find_datasets` and `get_dataset`:

| class | meaning | how it's set |
|---|---|---|
| `open` | the publisher states an open licence (OGL, CC-BY, CC0, ODbL, public domain…) | today's `open_licence` test |
| `open-inferred` | open by rule, not by statement (US federal works) | `atlas/licences.py` |
| `esri-mla` | Esri Master License Agreement or Esri terms of use | licence text pattern; Living Atlas items |
| `restricted` | the publisher states limits: non-commercial, no redistribution, WDPA-style terms | pattern list, reviewed |
| `stated` | some other licence text we can't classify | licence text present |
| `unknown` | nothing stated | empty |

Plus an optional input on `find_datasets`, `exclude_licence_class: ["esri-mla", ...]`. `open_licence` stays as it is.
Work: half a day, computed at publish time (no recrawl), and one new D1 column, which forces a full reload of about
255k rows (fine on Workers Paid).

## (c) Prefer the publisher's own service over an Esri copy

- Mark Living Atlas copies: `source: "esri-living-atlas"` (from `discovered_via`) on each result.
- When a dataset from the publisher's own server matches a Living Atlas copy (same normalised title, overlapping
  extent, same publisher after normalising credits), the own service ranks first. The copy gets `copy_of: <id>`
  and is ranked after it, but isn't removed, because some Esri copies add value (tiling, cleaned fields).
- This only helps where we've crawled the publisher's own server. NOAA, USFS and Environment Canada are in the US and
  CANZ waves; NASA FIRMS isn't anywhere yet, see (a).

## (b) A "trusted global service" tier

- `vocab/trusted.yaml`: a short, reviewed list of publishers and the hosts they serve from. The suggested start
  list is Tobler's: NASA (earthdata, firms.modaps.eosdis.nasa.gov, gibs), ESA/Copernicus (Copernicus Land, Marine,
  CDS, Sentinel Hub public), NOAA, USGS, UNEP-WCMC, GEBCO, EMODnet and FAO.
- Output field `trusted: true` and optional input `trusted_only: true`. Trusted datasets also get a small ranking
  boost.
- Trust is by host, not by the publisher name we read, so an Esri copy that credits NOAA isn't "trusted" (that's
  (c)'s job).

## (a) Key-gated services such as NASA FIRMS

- Catalogue them like any other service, with `access: "key"` and `key_ref: "FIRMS_MAP_KEY"`, the name of a secret
  held by the atlas Worker. The key never appears in `get_dataset` URLs or in published files.
- `fetch_features` adds the key on the way out. For FIRMS: the area CSV/JSON API by day range and sensor (VIIRS
  S-NPP, NOAA-20, NOAA-21, MODIS), turned into GeoJSON points.
- FIRMS isn't an ArcGIS or OGC service, so this is a small adapter in the Worker (one per key-gated API), plus
  hand-written catalogue records in `vocab/seeds/global.yaml` (kind: record).
- Rate limits: a MAP_KEY has a transaction allowance per time window. Everything through the atlas would share one
  key, so the Worker needs a per-key budget and an honest "rate limited, try later" error.

## Order and effort

1. (d) licence class: half a day. Unblocks Tobler's Esri filtering straight away.
2. (b) trusted tier: half a day once the list is agreed.
3. (c) own service over the Esri copy: a day, mostly matching and ranking tests.
4. (a) FIRMS through the atlas: a day for FIRMS. Each further key-gated API is about half a day.

## Decisions needed from Rob

- (a) A FIRMS MAP_KEY for the atlas (free, registered to an email address). Is the atlas allowed to use it on behalf
  of Tobler's users, and should there be one key for both or separate keys? Tobler already holds one in its own Worker.
- (b) Confirm the trusted list, and whether "trusted" should also cover national mapping and survey agencies (BGS,
  Ordnance Survey, NSTA…) or stay global only.
- (d) Whether `restricted` should cover non-commercial licences (CC-BY-NC, WDPA), so Tobler can exclude them for
  commercial use. This touches licences with commercial consequences.

## Rob's answers (18 Nov)

- **FIRMS:** yes in principle for Tobler to use through the atlas. Keys that users hold and enter themselves are
  wanted longer term but not in scope now. The key goes in as a Worker secret (Rob sets it; it's never handled in chat).
- **Trusted list:** much bigger than Tobler's first pass, perhaps a couple of hundred, including national agencies
  (BGS, Ordnance Survey, NSTA…). It needs to be semi-maintainable: see the publisher registry proposal in the
  handover and the chat of 18 Nov. Next step: agree that design, then build it before the `trusted` field.
