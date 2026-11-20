# AI Living World Atlas: handover (20 Nov 2026)

Start here when picking the atlas up in a new chat. The detailed history of decisions is in `docs/decisions.md`.

## How we work (decided 17 Nov)

- **The atlas has its own chat.** Tobler has a separate one. Neither edits the other's repo.
- **`docs/mcp-tools.md` is the contract** between them: the tools, fields and concept ids Tobler relies on. Keep them working; announce any change there first. Tobler's requests for new atlas features are listed there too.
- A Tobler change should never wait on an atlas deploy, and an atlas deploy should never break Tobler without a note in that file.

## What it is

An open, AI-first index of the world's public map services at layer level: ArcGIS REST, WMS/WFS/WMTS/WCS,
OGC API and download/cloud sources. Think of it as an open alternative to Esri's Living Atlas. The aims:

- good metadata, standard tags and an honest quality score;
- automated, rolling checks, so Rob stays hands-off;
- a data source for Tobler (asktobler.com), Rob's chat-driven GeoAI workspace, through a key-protected MCP server.

## Where things live

| Thing | Where |
|---|---|
| Code | github.com/pushpingeo/ai-living-world-atlas (branch `main`) |
| Viewer | pushpingeo.github.io/ai-living-world-atlas (GitHub Pages, MapLibre + OpenFreeMap positron) |
| MCP server | https://atlas-mcp.robdunfey.workers.dev/mcp (Cloudflare Worker `atlas-mcp` + D1 database `atlas`) |
| Crawl results | orphan branches `results/spike-<wave>` (large parquet files split into `-000`, `-001` parts) |
| Tags | `results/tags-<wave>`; re-tags from the liveness sweep in `results/tags-sweep` |
| Liveness | `results/liveness`: state.parquet (one row per published endpoint), REPORT.md, history.csv |
| Tag backups | GitHub release `tags-backup` (dated, never overwritten) and Cloudflare R2 bucket `atlas-backup/tags/` |
| Decisions log | `docs/decisions.md` |

GitHub secrets (Rob set them; never print or handle the values):

- `ANTHROPIC_API_KEY`
- `ATLAS_MCP_KEY`: the MCP access key. The server stays private until Rob says otherwise.
- `CLOUDFLARE_API_TOKEN`: D1 edit, Workers and R2 edit.
- `CLOUDFLARE_ACCOUNT_ID`

Cloudflare is on Workers Paid ($5/month); Rob may switch it off after the main build. **Since the spatial index (18 Nov)
the D1 database is ~660 MB, over the free plan's 500 MB**: switching Paid off needs a trim first (see decisions.md).

## How it runs

Everything runs on GitHub Actions. To trigger a workflow, edit its run file under `runs/` and push to `main`.
Results come back on the `results/*` branches.

| Workflow | Run file | What it does |
|---|---|---|
| `spike` | `runs/spike-<wave>.env` | Crawls a wave in parallel shards, then merges. Settings: `PREHARVEST=1` harvests big catalogues once; `CONCAT=1` merges without regrouping, for very large waves. When the source wave of `runs/collections.env` merges, it starts `collections` itself. |
| `remerge` | `runs/remerge.env` | Redoes only the merge from an earlier run's shard artifacts (kept 7 days). |
| `collections` | `runs/collections.env` | Groups local development plans into one dataset per council. Europe is derived this way: `spike-inspire` becomes `spike-europe`. |
| `tag` | `runs/tag-<wave>.env` | Haiku 5.5 tagging through the Batch API. Splits into several batches, skips datasets already tagged, and writes `COST.md`. To resume, set `BATCH_ID=id1,id2,...`. Refuses more than `MAX_DATASETS` (default 200k, about $18). Always started by hand. |
| `sweep` | `runs/sweep.env` (also nightly, 03:23 UTC) | Rolling liveness sweep, see below. Edit the run file and push to run it now. |
| `backup` | automatic | Runs after every tag run and every sweep (only saves tag sets that changed). |
| `pages` | automatic | Rebuilds the viewer from the waves listed in `runs/published.txt`, with the liveness sweep applied. Passing datasets only. Runs after spike, tag and sweep. |
| `deploy-mcp` | automatic | Incremental D1 load using row hashes on `results/mcp-deploy`, loaded in roughly 4 MB pieces, then a smoke test. |
| `eval-tags`, `check-key`, `probe` | their own run files | Tag-quality check, secret check, and fetching URLs the workspace itself can't reach. |

Workspace notes:

- The Claude workspace can only reach GitHub, the package registries and `*.arcgis.com`.
- Anything else, such as data.europa.eu or github.io, goes through an Actions workflow (`probe` is the quick one).
- `gh api` with REST works for Actions runs and logs; GraphQL is blocked.
- For local testing, use Playwright with google-chrome for the viewer, and `wrangler dev` with a local D1 for the MCP server.

## Current state

| Wave | Datasets | Passing | Notes |
|---|---|---|---|
| UK (`spike-gb`) | ~40k | ~10.9k | First wave, most tuned |
| Global backbones (`spike-global`) | 46.5k | 11.4k | UNEP-WCMC, GEM, GEBCO, Copernicus/EEA, ESA, GHSL, HydroSHEDS, USGS, FAO, public Living Atlas |
| Canada/Australia/NZ (`spike-canz`) | 143k | 52.2k | 96% live |
| US (`spike-us`) | 453k | 70.8k | 97% live; descriptions are sparse |
| Africa (`spike-africa`) | 17.6k | 8.7k | National-authority rule; petroleum layers from Morocco, Uganda, Angola |
| Values (`spike-values`) | 40 | 40 | Curated sources that return a value at a point: depth (GEBCO_2026, NOAA), ship density (World Bank/IMF), land elevation in 12 countries plus GLO-30 (19-20 Nov; tagged for under $0.01) |
| EMODnet (`spike-emodnet`) | 4.2k | 2.5k | First in publish order; WFS+WMS grouped, CC-BY from GeoNetwork |
| Europe (`spike-europe`) | 2.57M | 118.7k | From data.europa.eu (rerun 17 Nov: 681k catalogue records, was 367k); 466k local plans grouped into 1,849 council collections |

- The viewer and the MCP server hold about **264k passing datasets**, all tagged (18 Nov).
- Tagging spend is **$28.46** in total: UK $4.76 (including the quality check), global $1.14, CANZ $5.08, US $6.39,
  Europe $11.09 ($6.49 first run, $4.60 for the 51,981 new datasets from the 17 Nov rerun).
- At batch rates, tagging costs about **$0.09 per 1,000 datasets**.

## Watch out

- **The MCP Worker reads dataset details from the viewer's detail files on GitHub Pages** (`data/dz/xxx.json.gz`).
  Changing the viewer's data layout changes the MCP server: treat it as a contract change (`docs/mcp-tools.md`).
  This broke `get_dataset`/`fetch_features` for an hour on 17 Nov. `mcp-check` (push `runs/mcp-check.env`) tests the
  three tools Tobler uses live; the deploy smoke test now opens a dataset too.

## Rules Rob set

- Keep the MCP server key-protected.
- Report API costs as they happen, and ask before any tagging run over about $20.
- Ask before big or hard-to-undo choices. Otherwise make a sensible call and say so.
- Test properly, including in the browser, and say plainly what was and wasn't tested.
- Anything public must read as if a person wrote it.
- Keep Rob's involvement minimal.

## Liveness sweep (built 17 Nov)

`atlas/sweep.py`, nightly via the `sweep` workflow. Details and reasoning in `docs/decisions.md` (17 Nov).
- Rechecks published services: resolving every 7 days, failing every 3, retired every 28; up to 45k services a night.
  The published index is 508k endpoints on 181k services, so the first full pass takes about four nights.
- One visit per service: metadata (service JSON + /layers, or GetCapabilities) plus one small data request on one
  layer, rotating weekly. Tells us: resolves, layer still listed, text changed, returns data.
- Retires an endpoint after 3 failed checks over 14+ days (30 if the whole host was down). Retired endpoints come
  back if they answer again.
- Publisher text edits are measured against the first visit's baseline, then re-tagged in the same run
  (`results/tags-sweep`). Over 50k in a night is treated as a bug, not re-tagged.
- combine.py applies it at publish time: retired endpoints out, `"status":"failing"` on failing ones, latest data
  check in `check`, refused ArcGIS Query removed from capabilities. The viewer shows "not answering" or
  "sample request failed" against an endpoint.
- First full night (17 Nov, 45k services, 197 min, 107k requests): **99.6% of checked endpoints resolve**; 142k of
  508k endpoints checked so far; 539 failing, none retired yet. Hosts down that night: geoportal.kreis-lup.de,
  gis.dot.nv.gov, vogis.cnv.at. Data checks on record: 41.3k ok, 1.7k fail, 1.2k unchecked, 159 empty.
- Earlier test runs (3k and 4k services) gave 99.8%. Fixing our own WFS
  check (2.0.0 first; advertised GetMap/GetFeature address; upper-case parameters) took WFS sample failures from
  86% to under 2%.

## Spatial index (18 Nov, evening)

`find_datasets` now reads a quadtree cell key table, `ds_cell` (1.88M keys: home country + cell, and concept + home +
cell), instead of scanning the extent indexes. Built in `atlas/api_data.py` (`cell_keys`), read by `cellSelect` in
the Worker: keep the two in step, and bump `CELLS_VERSION` if keys are made differently (forces a full reload).
Live rows read per search (mcp-check, `debug: true` shows `rows_read` and `index`):

| Search | Before | Now |
|---|---|---|
| Edinburgh 5 km | 271k (+ count) | 25k |
| Edinburgh road, query, line | 264k | 330 |
| Gulf of Mexico, oil-gas | 264k | 849 |
| US protected-area | 264k | 10k |
| Nigeria, no text | 264k | 17k |
| UK, no text | 36k + 160k count | 84k |

- Area and concept searches return every match as a slim row, ranked and folded in the Worker; full rows are read for
  the kept 100 only. `matches` is exact (up to 20,000).
- Large areas without a concept: the Worker counts the area's keys (up to 20k). Few: cells. Many: the 60k best-scored
  datasets world-wide from the rank index (which now covers extent and home), as a sample (`matches_capped`).
- Text (FTS) and `include_other_countries` use the old paths.
- `datasets` is WITHOUT ROWID. Full reload: 338 MB of SQL, 84 pieces, ~8 minutes, tables swapped at the end.
- Testing: rebuild the published data with `bash .github/actions-fetch.sh` (2.5 min), `python -m atlas.api_data`,
  load the SQL into SQLite and copy the file over the local D1 file under `worker/.wrangler/state/v3/d1/`, then
  `wrangler dev --local` (set `database_id` to any UUID and put `ATLAS_KEY` in `worker/.dev.vars`; both are
  ignored by git). Local D1 reports the same rows_read as the live one.

## Search changes for Tobler (17 Nov, from the Tobler chat)

- `find_datasets` returns each dataset's `geometry` (point/line/polygon from the ArcGIS crawl; known for 128k of 256k, most WFS say only "features") and takes `geometry` to filter (unknowns kept).
- It also leaves out national publishers' datasets whose country doesn't touch the area (`home` column; country areas with 3° of waters in `vocab/country_areas.geojson`; any European country admits "EUROPE" datasets; international publishers and `vocab/extent_overrides.yaml` entries are always kept). `include_other_countries` widens it. This stopped Kentucky wells and US census blocks coming up for Nigeria.
- New D1 columns `gtypes` and `home`: a change in table layout now forces a full reload (`__schema__` in rows.json). Every SQL statement is on one line, because the deploy cuts load files at lines ending in ";".
- `parts get` streams part by part and takes a column list, so a small machine can read Europe's layers.
- Tobler now uses the MCP server live, through a service binding from a Worker (today `north-sea-geo-demo`, route `/atlas`; moving to Tobler's own Worker in the Tobler chat). Keep the Worker name `atlas-mcp`: the binding points at it.

## Known gaps and next steps (rough priority)

1. **Watch the sweep's first week.** history.csv on `results/liveness` now has one line per run, with `trigger`
   and `started` (UTC). Check the resolving rate, which hosts go "down", the second-look count, and that nothing
   retires wrongly once the 14-day window opens (around 1 Dec).
   - 17 Nov had two full runs (00:22 push, 12:07 scheduled; GitHub started the 03:23 schedule nearly 9 hours late).
     After both: 562k published endpoints on 195k services, 231k endpoints checked (41%), 99.3% resolving, 1,540
     failing. 111k services are still unchecked, so the first full pass finishes around 20 Nov; after that a night
     is ~28k services plus failing ones, well inside 45k and 240 minutes.
   - 18 Nov: GitHub never started the 03:23 run; started by hand at 09:02. The sweep now has four daily slots
     and skips once today's run is in history.csv (works: the 09:23 slot skipped). Results: 99.5% resolving, second
     look answered 24 of 106, 64% of endpoints checked once. Fixed: GEM `geojson` endpoints weren't checked
     (showed failing). Still to confirm: Overture S3 (rechecked 20 Nov), GEM back to ok (by 21 Nov), first
     retirements from ~1 Dec.
   - Fixed 17 Nov evening (decisions.md): failed services get a slow second look at the end of a run (some live
     servers take 40-60 s), S3 folder URLs are listed rather than fetched, and history no longer overwrites a
     same-day run. The first real test of the second look is the 18 Nov night run: check REPORT.md says how many
     answered and that the run still finishes inside its time.
   - Known real failures to expect retired from ~1 Dec: oceandata.rad.rutgers.edu (timeouts), gis1.mgipu.hr (502,
     300 endpoints on one WMS), gis12.cookcountyil.gov (404).
2. **US quality.**
   - Licences (17 Nov): the gap was missing licence statements, not wording. Rob approved inferring public domain
     for US federal works: `atlas/licences.py`, applied at publish time, labelled "inferred" in the licence text.
     3,228 published datasets marked open, 347 skipped where the credit names a non-federal party (5,420 on the US wave alone; the rest of those also appear in an earlier wave, which wins and carries its own publisher type). See `docs/us-licences.md`.
   - Still open: almost no US layers are joined to data.gov or Hub catalogue records (158 of 2,076 catalogues gave
     records). That join is the way to real licences for state and local data, and better US descriptions.
3. **Global source failures** (probed 17 Nov; all on their side, nothing to fix in our code):
   - Terrascope: resets the connection within half a second, from GitHub's runners. Looks like a block on cloud
     addresses. Only fixable by asking VITO.
   - FAO io.apps GeoServer: 502 on every path, down at their end.
   - UNEP-WCMC proxied ImageServers: their proxy's stored credentials fail ("Unable to generate token").
   - GFW tiles: blocked by robots.txt.
4. **Smaller items.**
   - 19 Nov: ArcGIS layers that can't page (Historic Environment Scotland) refused `resultRecordCount`; `fetch_features`
     and the viewer now retry without it (decisions.md). The viewer side still needs a look in a real browser.
   - Trim long credit strings used as publisher names.
   - Add WMTS/WCS data checks (the sweep checks they resolve, not that they return tiles/coverages).
   - Work out true footprints for false extents (they are flagged and ranked down; national ones are now also filtered by home country, see above).
   - Add an admin-area hierarchy.
   - Proposed new concepts: landscape-character-area, habitat-network, great-crested-newt-risk-zones.
   - The viewer's header still says "Public map services from UK government and agencies" (public text: Rob's call).
5. **Tobler integration.** Done 17 Nov (see above). Tobler's requests live in `docs/mcp-tools.md`; the name index there is parked by Rob.
6. **Size limits.** GitHub Pages is capped at 1 GB. Since 17 Nov the detail shards are gzipped and keyed by 3
   characters (`data/dz/`), so the site is **203 MB** (was 702 MB). A separate `size-limit` job fails at 800 MB, so
   GitHub emails a failure; the deploy still runs. R2 is the next step if it ever grows that far
   (`docs/viewer-data-size.md`). Not yet tested in Safari or Firefox.
7. **Actions concurrency.** The free plan runs 20 jobs at once; a 20-shard wave queues everything else (including the
   sweep) until shards finish.
8. **Africa.** Published 18 Nov: 8,688 passing datasets (tagged for $0.76), after Rob's national-authority rule.
   Includes ONHYM (Morocco), the Petroleum Authority of Uganda (slow server, ~30 s fetches) and ANPG's own server.
   GNPC (Ghana), Kenya's petroleum department and ANPG's ArcGIS Online services need a login token, so they're out.
   Nigeria and Tanzania still need domain discovery (`docs/spikes/africa-scoping.md`). FNDS (Mozambique) brings some
   untidy work layers ("xtemp") under the new rule. The rule is **a trial for Africa only** (Rob, 18 Nov): judge
   whether it helps or adds noise before extending it (`AUTHORITY_PASS_COUNTRIES` in quality.py).
9. **Tobler requests** (`docs/mcp-tools.md` has the log). EMODnet wave published 17 Nov (first in
   `runs/published.txt`, tagged for $0.14). NSTA status words done. Text search done 18 Nov (FTS5). Spatial index
   done 18 Nov (above). Name index: waiting on Rob's licence call; names only, no outlines.
   - **Trusted services / publisher registry** (`docs/publisher-registry-design.md`, Rob's decisions 18 Nov):
     stage 1 built: `vocab/publishers.yaml` (seeded: BGS, NSTA, Ordnance Survey hosted by Esri UK, Esri UK as a
     platform), `atlas/publishers.py`, and the `publishers` workflow (weekly candidate issue, Rob ticks and closes,
     `apply` writes the registry). First list: 250 candidates in issues #2-#13, 25 each, ranked by services; Rob
     approves an issue with one comment (`add all`, `add all except <codes>`). **Stage 2 waits for those**: registry
     applied at publish time and in D1 (`publisher_id`, `trusted`, `hosted_by`, `publisher_credit`,
     `trusted_only`), with the licence classes in the same full reload. No licence defaults from the registry.
10. **Hosted download datasets** (18 Nov). `atlas/files.py` turns a publisher's download into gzipped GeoJSON tiles
    in `files/<id>/` (10° cells plus `index.json`, published at `data/f/<id>/`) and a catalogue record in
    `vocab/seeds/files.yaml`; the `spike-files` wave (first in `runs/published.txt`) lists them, and `fetch_features`
    reads only the tiles near the area (all tiles, 12 at a time, for a text search). Specs: `vocab/files/*.yaml`.
    - **Live: 18 GEM trackers** from Rob's `gem-data.zip` (~192k features, 26 MB gzipped, all CC BY 4.0 per each
      About sheet): extraction fields, gas and oil/NGL pipelines (routes), LNG terminals, oil and gas plants, coal
      plants, mines and terminals, wind, solar, hydro, geothermal, bioenergy, nuclear, steel, cement, chemicals,
      iron ore mines. Live checks 0.1-1.0 s each.
    - **Left out on licence grounds:** TransitionZero-sourced solar rows (CC BY-NC, 18,732), the integrated power
      tracker, the methane tracker (plumes CC BY-NC-SA), coal mine boundaries (no licence stated). Ownership,
      finance and LNG-carrier tables aren't maps; they could become a "who owns this" lookup later.
    - **To refresh** when GEM releases: put the new file in a folder, update `source`/`release`/`citation` in the
      spec, run `python -m atlas.files --source-dir DIR vocab/files/<id>.yaml`, bump `runs/spike-files.env`, push.
      Raw downloads stay out of git (size).

11. **Values at a point** (19 Nov, Tobler request; `docs/decisions.md` has the table of checked values). Capability
    `sample` = the endpoint returns a number at a point. Added at publish time (`atlas/sampling.py`, rules in
    `vocab/sample_rules.yaml`): one-band ImageServers (identify), WCS, and hand-checked WMS feature-info; never
    exaggerated relief, hillshades or colour ramps. Curated value sources are records in `vocab/seeds/values.yaml`
    (wave `spike-values`) that carry their own `info.sample`. Hand-recorded licences, attribution lines and terms live
    in `vocab/licence_overrides.yaml` (also publish time), shown by `get_dataset` as `attribution` and `terms`.
    `mcp-check` reads a value through each sampled endpoint at the North Sea and Niger Delta points.
    - Open: shipping density comes from Esri's tiles-only copy (LERC decoding). Hosting the World Bank GeoTIFFs as a
      COG on R2 would make it a plain range read; Rob's call (storage).
    - Open: GEBCO's OPeNDAP at CEDA is slow (6-8 s a cell). The UNH CCOM image service is the fast route.
    - **Land elevation (20 Nov):** curated records for Scotland (50 cm national lidar COGs, 18 lidar surveys via WMS),
      France, Japan, Switzerland (point APIs), Spain, Norway, North Rhine-Westphalia, Canada (WCS), Netherlands (AHN
      feature-info), Australia (GA MapServer identify, checked by hand: GA's CDN refuses GitHub) and Copernicus GLO-30
      (COGs on AWS, no CORS). England's EA lidar WMS and the US 3DEP ImageServer were already in and now sample.
      New methods `api` and `cog`; `atlas/sample_check.py` reads values the way an agent would, and mcp-check runs it
      at 15 points. Table of values in decisions.md (20 Nov).
    - Next for elevation: New Zealand from LINZ's own 1 m COGs (STAC, CC BY 4.0; the Eagle-hosted NZ service in the
      atlas is "for use with ArcGIS software"); Germany's other states (Hessen refused GitHub); Flanders' WCS axis
      names; Denmark, Finland, Sweden need keys or accounts.
    - CEDA's OPeNDAP answered 403 to one run and 200 to the next: watch it in mcp-check.
    - CEDA and Esri's tiled image services refuse crawlers in robots.txt. We respect that: a curated record there
      shows `unchecked` ("checked by hand"), and the sweep will report it as robots, not failing.
    - The generic rule trusts identify on one-band ImageServers. mcp-check is how false positives show up (Esri's
      WorldElevation3D answered 0 everywhere and is now excluded); add any others to `never` in sample_rules.yaml.
