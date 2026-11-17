# AI Living World Atlas: handover (17 Nov 2026)

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

Cloudflare is on Workers Paid ($5/month); Rob may switch it off after the main build.

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
| Europe (`spike-europe`) | 2.57M | 118.7k | From data.europa.eu (rerun 17 Nov: 681k catalogue records, was 367k); 466k local plans grouped into 1,849 council collections |

- The viewer and the MCP server hold about **256k passing datasets**, all tagged.
- Tagging spend is **$28.46** in total: UK $4.76 (including the quality check), global $1.14, CANZ $5.08, US $6.39,
  Europe $11.09 ($6.49 first run, $4.60 for the 51,981 new datasets from the 17 Nov rerun).
- At batch rates, tagging costs about **$0.09 per 1,000 datasets**.

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
   - Fixed 17 Nov evening (decisions.md): failed services get a slow second look at the end of a run (some live
     servers take 40-60 s), S3 folder URLs are listed rather than fetched, and history no longer overwrites a
     same-day run. The first real test of the second look is the 18 Nov night run: check REPORT.md says how many
     answered and that the run still finishes inside its time.
   - Known real failures to expect retired from ~1 Dec: oceandata.rad.rutgers.edu (timeouts), gis1.mgipu.hr (502,
     300 endpoints on one WMS), gis12.cookcountyil.gov (404).
2. **US quality.**
   - Licence detection doesn't recognise "public domain" wording, so no US licence is marked open.
   - Almost no US layers are joined to data.gov or Hub catalogue records (158 of 2,076 catalogues gave records).
3. **Global source failures.**
   - Terrascope: connection reset.
   - FAO map server: 502.
   - GFW tiles: blocked by robots.txt.
   - Some UNEP-WCMC proxied ImageServers.
4. **Smaller items.**
   - Trim long credit strings used as publisher names.
   - Add WMTS/WCS data checks (the sweep checks they resolve, not that they return tiles/coverages).
   - Work out true footprints for false extents (they are flagged and ranked down; national ones are now also filtered by home country, see above).
   - Add an admin-area hierarchy.
   - Proposed new concepts: landscape-character-area, habitat-network, great-crested-newt-risk-zones.
   - The viewer's header still says "Public map services from UK government and agencies" (public text: Rob's call).
5. **Tobler integration.** Done 17 Nov (see above). Tobler's requests live in `docs/mcp-tools.md`; the name index there is parked by Rob.
6. **Size limits.** GitHub Pages is capped at 1 GB. Measured 17 Nov: the viewer site is **702 MB** (detail shards
   `data/d` 628 MB, tiles 72 MB), up from ~560 MB before the Europe rerun. The pages build now prints the size and
   warns at 800 MB. One more large wave would push it over: plan to move the detail shards to R2 before the next one.
7. **Actions concurrency.** The free plan runs 20 jobs at once; a 20-shard wave queues everything else (including the
   sweep) until shards finish.
