# AI Living World Atlas: handover (27 Nov 2026, 17:15)

Start here when picking the atlas up in a new chat. The detailed history of decisions is in `docs/decisions.md`.

## How we work (decided 17 Nov)

- **The atlas has its own chat.** Tobler has a separate one. Neither edits the other's repo. Both share the Claude project "Tobler"; an atlas chat may attach `pushpingeo/ai-living-world-atlas` with push access (Rob, 24 Nov). Tobler's repo is read-only from here (public, so a plain clone works).
- **`docs/mcp-tools.md` is the contract** between them: the tools, fields and concept ids Tobler relies on, and since 25 Nov the hosted OpenStreetMap copy's file layout and manifest format. Keep them working; announce any change there first. Tobler's requests for new atlas features are listed there too.
- A Tobler change should never wait on an atlas deploy, and an atlas deploy should never break Tobler without a note in that file.

## What it is

An open, AI-first index of the world's public map services at layer level: ArcGIS REST, WMS/WFS/WMTS/WCS,
OGC API and download/cloud sources. Think of it as an open alternative to Esri's Living Atlas. The aims:

- good metadata, standard tags and an honest quality score;
- automated, rolling checks, so Rob stays hands-off;
- a data source for Tobler (asktobler.com), Rob's chat-driven GeoAI workspace, through a key-protected MCP server;
- since 25 Nov, a host for data the atlas publishes itself (first: the OpenStreetMap copy Tobler's site checks read).

## Where things live

| Thing | Where |
|---|---|
| Code | github.com/pushpingeo/ai-living-world-atlas (branch `main`) |
| Viewer | pushpingeo.github.io/ai-living-world-atlas (GitHub Pages, MapLibre + OpenFreeMap positron) |
| MCP server | https://atlas-mcp.robdunfey.workers.dev/mcp (Cloudflare Worker `atlas-mcp` + D1 database `atlas`) |
| Crawl results | orphan branches `results/spike-<wave>` (large parquet files split into `-000`, `-001` parts) |
| Tags | `results/tags-<wave>`; re-tags from the liveness sweep in `results/tags-sweep` |
| Liveness | `results/liveness`: state.parquet (one row per published endpoint), REPORT.md, history.csv |
| Tag backups | GitHub release `tags-backup` (dated, never overwritten) and Cloudflare R2 bucket `atlas-backup/tags/` (private) |
| Hosted data | Cloudflare R2 bucket `atlas-data` (public to read), `https://data.asktobler.com/`, CORS set for range requests. `osm/` holds the OpenStreetMap copy |
| OSM copy reports | `results/osm`: per market the last report, manifest and the record as it would be written; `RUNS.txt` logs every run |
| Decisions log | `docs/decisions.md` |

GitHub secrets (Rob set them; never print or handle the values):

- `ANTHROPIC_API_KEY`
- `ATLAS_MCP_KEY`: the MCP access key. The server stays private until Rob says otherwise.
- `CLOUDFLARE_API_TOKEN`: D1 edit, Workers and R2 edit (both buckets). The osm workflow derives R2 S3 credentials from it (`osm/r2-s3-env.sh`) for multipart uploads over 300 MiB.
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
| `pages` | automatic | Rebuilds the viewer from the waves listed in `runs/published.txt`, with the liveness sweep applied. Passing datasets only. Runs after spike, tag and sweep, and on a push of `runs/published.txt` (so a new wave shows untagged for a few minutes if its tag run is pushed at the same time). |
| `deploy-mcp` | automatic | Incremental D1 load using row hashes on `results/mcp-deploy`, loaded in roughly 4 MB pieces, then a smoke test. |
| `osm` | `runs/osm.env`; weekly per market listed in `runs/osm-weekly.env` | The hosted OpenStreetMap copy, see below. Can also be started by REST dispatch with `market` and `publish` inputs. |
| `eval-tags`, `check-key`, `probe` | their own run files | Tag-quality check, secret check, and fetching URLs the workspace itself can't reach. |

Workspace notes:

- The Claude workspace can only reach GitHub, the package registries and `*.arcgis.com` (including the ArcGIS Online search API, useful for finding a body's own organisation and owners). Not Geofabrik, not data.asktobler.com.
- Anything else, such as data.europa.eu or github.io, goes through an Actions workflow (`probe` is the quick one).
- `gh api` with REST works for Actions runs and logs; GraphQL is blocked (so `gh issue list` and `gh workflow run` fail; use `gh api repos/.../issues` and `gh api repos/.../actions/workflows/<file>/dispatches`).
- For local testing, use Playwright with google-chrome for the viewer, and `wrangler dev` with a local D1 for the MCP server.

## Current state

| Wave | Datasets | Passing | Notes |
|---|---|---|---|
| UK (`spike-gb`) | ~40k | ~10.9k | First wave, most tuned |
| Global backbones (`spike-global`) | 46.5k | 11.4k | UNEP-WCMC, GEM, GEBCO, Copernicus/EEA, ESA, GHSL, HydroSHEDS, USGS, FAO, public Living Atlas |
| Canada/Australia/NZ (`spike-canz`) | 143k | 52.2k | 96% live |
| US (`spike-us`) | 453k | 70.8k | 97% live; descriptions are sparse |
| Africa (`spike-africa`) | 17.6k | 8.7k | National-authority rule; petroleum layers from Morocco, Uganda, Angola |
| Best-in-class fill (`spike-fill`) | 5.1k | 463 | 24 Nov night: NASA, USGS National Map and earthquakes, Met Office, EFFIS, FIRMS, SoilGrids, GVP, WRI, World Bank. Last in publish order. See below |
| UK water and peat (`spike-ukwaterpeat`) | 13 | 13 | Storm overflows (8 companies live, 2025 annual returns, Scottish Water) and the England Peat Map (24 Nov) |
| Screening zones (`spike-zones`) | 11 | 11 | 26 Nov evening (Tobler): HSE consultation zones (restricted, no data), Natura 2000 NL, FEMA NFHL flood hazard zones, EPA Sole Source Aquifers, Texas well capture zones (TCEQ, 6), California DWSAP (restricted) |
| US contamination (`spike-uscontamination`) | 21 | 21 | EPA's national layers (24 Nov, Tobler): Superfund, brownfields, RCRA corrective action, TRI, ICIS-Air, NPDES, RCRA TSD; 25 Nov: leaking tanks (UST Finder), Formerly Used Defense Sites, nonattainment areas (7 standards) |
| NL pollution (`spike-nlpollution`) | 7 | 7 | 25 Nov: Wbb decisions (Kadaster WKPB, OGC API), RIVM E-PRTR releases and drinking water zones, Zeeland and Noord-Holland former landfills |
| AU pollution (`spike-aupollution`) | 9 | 9 | 25 Nov: EPA Victoria, NSW EPA (3), Queensland, Tasmania, Geoscience Australia (2); the NPI is hosted in `spike-files` |
| UK pollution (`spike-ukpollution`) | 6 | 6 | Contamination step 2 (24 Nov, Tobler): SEPA authorisations, NRW permits, DAERA incidents and consents, NI historical land use |
| UK ground (`spike-ukground`) | 16 | 16 | Contamination step 1 (24 Nov, Tobler): landfill, coal mining risk, closed mining waste, source protection zones, radon, council records |
| UK pack (`spike-ukpack`) | 45 | 45 | Curated records for landscape, heritage, peat, farmland quality, flood zones, SSSI IRZs, per nation (23 Nov, Tobler) |
| UK protected (`spike-ukprotected`) | 24 | 24 | Curated records for UK statutory sites (22 Nov, Tobler): SAC, SPA, Ramsar, SSSI/ASSI, marine designations, ancient woodland per nation; JNCC offshore in `spike-files` |
| Values (`spike-values`) | 40 | 40 | Curated sources that return a value at a point: depth (GEBCO_2026, NOAA), ship density (World Bank/IMF), land elevation in 12 countries plus GLO-30 (19-20 Nov; tagged for under $0.01) |
| EMODnet (`spike-emodnet`) | 4.2k | 2.5k | First in publish order; WFS+WMS grouped, CC-BY from GeoNetwork |
| Europe (`spike-europe`) | 2.57M | 118.7k | From data.europa.eu (rerun 17 Nov: 681k catalogue records, was 367k); 466k local plans grouped into 1,849 council collections |

- The viewer and the MCP server hold about **267k passing datasets**, all tagged (plus the OSM copy records for the UK and NL, and the screening zones).
- Tagging spend is **$30.28** in total (26 Nov: screening zones, under a cent) (24 Nov: $1.79 contamination re-tags, $0.03 fill wave; under a cent each for the curated UK and US waves): UK $4.76 (including the quality check), global $1.14, CANZ $5.08, US $6.39,
  Europe $11.09 ($6.49 first run, $4.60 for the 51,981 new datasets from the 17 Nov rerun).
- At batch rates, tagging costs about **$0.09 per 1,000 datasets**.

## Watch out

- **The MCP Worker reads dataset details from the viewer's detail files on GitHub Pages** (`data/dz/xxx.json.gz`).
  Changing the viewer's data layout changes the MCP server: treat it as a contract change (`docs/mcp-tools.md`).
  This broke `get_dataset`/`fetch_features` for an hour on 17 Nov. `mcp-check` (push `runs/mcp-check.env`) tests the
  three tools Tobler uses live; the deploy smoke test now opens a dataset too.
- **ArcGIS Online search seeds:** the crawler now brackets the query (`(query) type:... access:public`). Before 24 Nov an
  unbracketed `owner:A OR owner:B` matched most of ArcGIS Online (119,745 items in one run).
- **The OSM copy's files are read by Tobler's page directly**, not through the MCP: the layout and manifest format in
  `docs/mcp-tools.md` are as binding as the tool fields. The manifest goes up last; never overwrite a release's files.
- **Geofabrik throttles heavy downloaders.** On 25 Nov, after about four UK builds in a day between the two repos, it
  refused connections (HTTP 000) for 4 of NL's 12 extracts and 8 of the UK's 50. Since 26 Nov the build backs off: a
  refused extract is tried again after about 15 minutes, then 30 (plus up to a minute of jitter; `RETRY_WAITS` in the
  build step), and one that fails three times is left out of the release and its outline. Worst case adds ~47 minutes.
  Don't run several builds back to back. **26 Nov:** the NL dry build (the day's second build, after the UK publish)
  still lost Flevoland and Noord-Holland on both tries. **27 Nov:** the plan job couldn't connect to Geofabrik at all
  (curl exit 7), yet a probe runner a minute later fetched the index and Flevoland at once (round 54), and a rerun of the
  failed job (fresh runner) built 12 of 12 with no refusals. So the refusals look tied to particular runner addresses,
  not to time: if a whole job is refused, rerun it (`POST .../actions/runs/<id>/rerun-failed-jobs`) rather than wait.
  A refused plan job publishes nothing and the last release stays live.

- **ArcGIS Online's shared hosts** (services2.arcgis.com and friends) carry thousands of organisations. Since 27 Nov the
  sweep's host cut-off, second look and host-down rule work per organisation there (`host_key` in sweep.py); before
  that, one organisation's blip marked 859 other services "host down" in a night.

## Rules Rob set

- Keep the MCP server key-protected.
- Report API costs as they happen, and ask before any tagging run over about $20.
- Ask before big or hard-to-undo choices. Otherwise make a sensible call and say so.
- Test properly, including in the browser, and say plainly what was and wasn't tested.
- Anything public must read as if a person wrote it.
- Keep Rob's involvement minimal.

## Hosted OpenStreetMap copy (25 Nov)

Taken over from Tobler (design: project doc `claude/osm-copy-design.md`; request: Tobler's `docs/atlas-requests.md`,
25 Nov; decisions.md 25 Nov). The atlas owns the bucket `atlas-data`, the build, refresh, licence and records; Tobler owns
the kinds and tags (`catalogue/osm-snapshot.json`), the reader (`js/osmsnapshot.js`) and the Overpass fallback.

- **Code:** `osm/` (`plan.py` picks the smallest Geofabrik extracts under a market's roots; `build.py` turns one filtered
  extract into one FlatGeobuf and one GeoParquet per group; `publish.py` writes the manifest and report; `record.py`
  writes the atlas record; `check_spec.py` compares `osm/spec.json` with Tobler's file; `r2-s3-env.sh` makes R2 S3
  credentials). Workflow `.github/workflows/osm.yml`: plan, up to `MAX_PARALLEL` build jobs, publish.
- **Spec:** `osm/spec.json` is a copy of Tobler's file; the build stops if Tobler's kinds, groups, keep_tags or version
  differ (the last release stays live). To take a Tobler change: copy those four keys across, keep `markets`, push.
- **Streaming build (atlas change, 25 Nov):** features go to lz4 Arrow files per group in 200k chunks, GDAL writes the
  FlatGeobuf from them (its spatial index does the Hilbert sort), and the GeoParquet is written batch by batch from the
  FlatGeobuf. Same features as Tobler's version (checked on a 1.5M-building test file and on the real UK: 42 extracts,
  identical counts per group and identical FlatGeobuf bytes). Peak memory for Ireland's 418 MB extract went from 7.4 GB to
  1.3 GB, so Texas (729 MB) and California (norcal and socal, about 670 MB each) should need about 2.2 GB on a normal runner.
- **Runs so far:** dry builds on 25 Nov (UK 50 of 50; NL 8 of 12 and UK 42 of 50 when Geofabrik refused some).
  **First atlas publish, UK, 26 Nov 06:38-06:50** (run 45769663315, Rob's go): 50 of 50 extracts, none carried, 7.62 GB
  FlatGeobuf, 3.09 GB GeoParquet, manifest 447 kB, release `osm/2026-11-26/`. Data still as of 24 Nov 21:21 UTC (Geofabrik
  had no newer UK extract that morning). Checked through `probe` round 52: manifest 200 with CORS for asktobler.com,
  range reads of a FlatGeobuf and a GeoParquet answer 206 with the right magic bytes. The 12 minutes (not 40) was the
  streaming build with six jobs.
- **Publishing:** `PUBLISH=yes` (or dispatch `publish=yes`) checks the token can write, uploads files to
  `osm/<release>/<extract>/`, then the manifest `osm/<market>.json`, then writes `vocab/seeds/osm.yaml` and commits it.
  Once `spike-osm` is in `runs/published.txt`, it also runs spike-osm, pages and deploy-mcp itself.
- **Records:** `osm-copy-<market>` (wave `spike-osm`), publisher OpenStreetMap contributors, licence via
  `vocab/licence_overrides.yaml` (host `data.asktobler.com`, layers `^osm-copy-`: ODbL 1.0, open, "© OpenStreetMap
  contributors"). The record id follows the manifest URL. The OSM copyright page's wording was written from what OSMF
  publishes but not re-read on 25 Nov (the workspace can't reach it): read it once in a browser.

**Still to do, in order:**
1. **First publish (done 26 Nov):** UK published, see "Runs so far". `uk` is in `runs/osm-weekly.env`, so the Saturday
   05:41 UTC cron rebuilds and publishes it from 28 Nov; `runs/osm.env` is back to `PUBLISH=no`. An extract a run can't
   build keeps its last entry (`carried`) if under 14 days old.
2. **First record (done 26 Nov):** `osm-copy-uk`, dataset id `0e3b9e398d081f86`, wave `spike-osm` (second in
   `runs/published.txt`, after spike-files), tagged for under a cent (concepts road, rail, power-line, building). Live
   checks through `mcp-ask`: `get_dataset` returns it with the manifest endpoint, release, data date and feature counts;
   a text search near Linlithgow finds it; a `road` search there ranks it 9th of 30, below DfT statistics layers (the
   best-in-class ranking work would fix that). Each publish now reruns spike-osm, pages and deploy-mcp itself.
3. **NL and AU dry builds, then publish each** (a day apart, for Geofabrik). **NL dry build, 26 Nov 07:23-07:36** (run
   45774894317): 10 of 12 extracts, Flevoland and Noord-Holland refused twice (HTTP 000); 10.4M features (9.8M
   buildings), 3.5 GB FlatGeobuf, 1.4 GB GeoParquet, peak memory under 1 GB per extract. Don't publish NL without
   Noord-Holland (Amsterdam): rerun the dry build on a quiet day first. **NL dry build retry, 27 Nov 06:15-06:26** (run
   45950777779, attempt 2 after the plan job couldn't connect): **12 of 12**, none carried, no refusals (so the new
   backoff wasn't exercised), 12.4M features, 4.19 GB FlatGeobuf, 1.69 GB GeoParquet, peak 908 MB, data as of 26 Nov
   21:21 UTC. **NL published 27 Nov 16:11-16:18** (run 46031400709, Rob's go): 12 of 12, release `osm/2026-11-27/`,
   12.4M features. Probe round 59: manifest 200 with CORS, Noord-Holland and Flevoland files answer range reads (206,
   right magic bytes). Record `osm-copy-nl`, id `227eacf1e3842a0f`, tagged for under a cent; `get_dataset` opens it live.
   `nl` is in `runs/osm-weekly.env` (Saturday 07:11 UTC, first on 28 Nov). **Next: AU dry build**, not on a Saturday. **US on hold (Rob, 25 Nov).** US: 54 extracts once the five regional
   bundles are skipped (check the plan line says 54); 6 shards is fine for disk (90 GB free per runner) and memory.
4. **Old releases (done 25 Nov):** an R2 lifecycle rule on `atlas-data` (Rob set it) deletes objects under `osm/20`
   30 days after upload. The prefix catches only the dated release folders, never the manifests (`osm/<market>.json`).
   30, not 14: a live manifest can point into a release up to 14 days old (`carried`) and then wait 7 days for the next
   run. `osm/health.py` reads the rule back from the Cloudflare API and checks each manifest's age; it runs in the
   nightly sweep (section "Hosted OpenStreetMap copy" in results/liveness REPORT.md) and on its own via `osm-health`
   (push `runs/osm-health.env`). It warns if a manifest is over 10 days old or points to files over 23 days old: the one
   way the rule could delete live files is weekly publishing stopping.
5. Cost at four weekly markets is about $4-5 a month of R2 storage with about four releases kept (30-day rule), plus about 17 GB of
   Geofabrik downloads a week.

## Liveness sweep (built 17 Nov)

**26 Nov evening, bug fixed:** curated endpoints (layer names `<record id>:<n>`) never matched a crawled layer's uid, so
the sweep marked them "missing" (51) or "unmatched" (60); the first would have retired about 7 Dec. They are now found by
layer URL (`match_key` in sweep.py; decisions.md). The failing ones clear on their next visit (every 3 days): check
REPORT.md on 27-29 Nov that curated records read "ok".

**27 Nov:** resolving fell to 98.0% (99.4% on 24 Nov). The biggest part was the host cut-off counting all of
services2.arcgis.com as one host; fixed the same afternoon (per organisation on shared ArcGIS Online hosts, decisions.md).
A live recheck found 1,326 of 1,334 services2 services fine, so the rate should recover as those come due again (3 days).
Curated records read "ok" on 27 Nov. FEMA NFHL is now checked by hand (`manual_check`), so the sweep leaves it out.

`atlas/sweep.py`, nightly via the `sweep` workflow. Details and reasoning in `docs/decisions.md` (17 Nov).
- Rechecks published services: resolving every 7 days, failing every 3, retired every 28; up to 45k services a night.
- One visit per service: metadata (service JSON + /layers, or GetCapabilities) plus one small data request on one
  layer, rotating weekly. Tells us: resolves, layer still listed, text changed, returns data.
- Retires an endpoint after 3 failed checks over 14+ days (30 if the whole host was down). Retired endpoints come
  back if they answer again.
- Publisher text edits are measured against the first visit's baseline, then re-tagged in the same run
  (`results/tags-sweep`). Over 50k in a night is treated as a bug, not re-tagged.
- combine.py applies it at publish time: retired endpoints out, `"status":"failing"` on failing ones, latest data
  check in `check`, refused ArcGIS Query removed from capabilities. The viewer shows "not answering" or
  "sample request failed" against an endpoint.
- **Time limit fixed 24 Nov evening, and it held on 25 Nov:** 168.5 minutes, all 45,000 due services checked (24 Nov had
  run 307 minutes). Now a service checks the clock only once it has a slot (256 first pass, 16 second look), and anything
  still running past the deadline is cancelled and stays due. REPORT.md says how many were cut.
- First full pass done 23 Nov: 577k published endpoints, 100% checked at least once; resolving 99.4% on 24 Nov, 99.1% on
  25 Nov. 24 Nov hosts down: all EEA discomap hosts (bio, climate, image, land, water), services.bgr.de, www.ine.es.

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
- Text (FTS) and `include_other_countries` use the old paths. A text search still needs an area (lon/lat or bbox).
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
- Tobler uses the MCP server live, through a service binding from its Worker. Keep the Worker name `atlas-mcp`: the binding points at it.

## UK protected sites and Tobler fixes (22 Nov)

Details in decisions.md (22 Nov) and the contract note in mcp-tools.md.
- `vocab/seeds/uk-protected.yaml`: 24 records, one per designation and nation, on each designating body's own feature
  service. Written by a one-off script from live metadata; to refresh counts and dates, re-read the layers and edit.
  Licences and attribution statements: `vocab/licence_overrides.yaml` (rules `^uk-...:`).
- Hosted from open downloads by the `files` workflow (`runs/files.env`, spec key `source_url`): JNCC offshore MPAs
  (`jncc-offshore-mpas`, version 20251203) and England's NSIP boundaries (`pins-nsip-england`, planning.data.gov.uk,
  refreshed daily at source: rerun `files` then bump `runs/spike-files.env` to refresh).
- **Record ids are fixed** (`record_id` in atlas/datasets.py): a hosted file takes its landing endpoint's uid, any
  other record its first endpoint's.
- Publish-time hand fixes (`atlas/hand_fixes.py`): concepts (`vocab/concept_overrides.yaml`) and publisher types by name
  (`vocab/publisher_type_overrides.yaml`).
- `mcp-ask` workflow: push `runs/mcp-ask.jsonl` (one call per line) for quick live MCP calls; results on `results/mcp-ask`.
- Workspace can't reach gis.daera-ni.gov.uk, JNCC or planning.data.gov.uk: use `probe`.

## The broadened UK pack (23 Nov)

Details in decisions.md (23 Nov) and the contract note in mcp-tools.md (with every record id).
- `vocab/seeds/uk-pack.yaml`: 45 records for landscape, heritage, peat, farmland quality, flood zones and the SSSI Impact
  Risk Zones, per nation, on each publisher's own service (wave `spike-ukpack`). Keyword `uk-screening-pack` lists them all.
- Two are not open on purpose: Carbon and Peatland 2016 (non-commercial licence) and Hutton's LCA (JHI licence unread).
- SSSI IRZ `irzcode` decoding: `vocab/sssi_irz_codes.json`, `docs/sssi-irz-codes.md`.
- Curated WFS records name their feature type in `info.type_name` (Worker and viewer use it).
- Reachable from GitHub but not from the workspace: inspire.hes.scot, map.sepa.org.uk, maps.gov.scot/server,
  datamap.gov.wales, gis.daera-ni.gov.uk, environment.data.gov.uk, druid.hutton.ac.uk, irz.geodata.org.uk.
  Refuse GitHub: maps.data.gov.scot (403), cagmap.snh.gov.uk (no answer), historicengland.org.uk and
  portal.historicenvironment.scot (403 bot checks).

## UK contamination, step 1 (24 Nov)

Details in decisions.md (24 Nov), the contract note in mcp-tools.md, and the project docs
`claude/contamination-and-pollution-screening.md` and `claude/contamination-tobler-reply.md`.
- `vocab/seeds/uk-ground.yaml`: 16 records (keyword `uk-ground-pack`).
- Every curated UK record carries `nation`, `completeness` (complete | partial) and `completeness_note` in its endpoint
  info.
- Most of these licences are not open, each with its reason (decisions.md). Radon accepted as OGL by Rob (24 Nov);
  EA landfill's Conditional Licence accepted for screening (still not open).
- The tag workflow takes `RETAG_CONCEPTS` and `RETAG_TITLE`. **Clear `BATCH_ID` in a run file before reusing it**.

## UK contamination, step 2 (24 Nov, afternoon)

- `vocab/seeds/uk-pollution.yaml`: 6 records (keyword `uk-pollution-pack`): SEPA authorisations, NRW installation and
  waste permits, DAERA pollution incidents (1 km) and trade discharge consents, NIEA historical land use.
- SEPA's SPRI and Defra's national AQMA layer aren't available as services.

## US contamination (24 Nov, afternoon)

- `vocab/seeds/us-contamination.yaml`: 10 EPA records (keyword `us-contamination-pack`). Public domain. Completeness is per
  federal programme; state lists aren't in them. 25 Nov: 11 more (see below).

## EA downloads, storm overflows, England Peat Map (24 Nov, evening)

- Hosted (`vocab/files/ea-*.yaml`, wave `spike-files`): EA industrial permits, waste permits, serious pollution incidents.
  Personal fields dropped by keep-list. **Monthly refresh on the 3rd** (`runs/files-monthly.env`, which also refreshes
  NSIP); the files job publishes its own refreshes. Check the first one on 3 Dec.
- Curated (`vocab/seeds/uk-water-peat.yaml`, wave `spike-ukwaterpeat`): 8 water companies' live storm overflows, the 2025
  annual returns (England and Wales), Scottish Water (not open), England Peat Map extent, observations, restoration.
- Still open: NRW incidents (manual quarterly download) and Scotland's Local Landscape Areas (Spatial Hub account),
  both Rob's call. Probe: a `FULL ` line keeps a small download whole; never use it on files with personal data.

## Pollution screening: US additions, Netherlands, Australia (25 Nov, night)

Gap review: project doc `claude/pollution-sources-gap-review-2026-11-25.md`. Contract note with every id in
docs/mcp-tools.md (25 Nov night); reasons in decisions.md.
- **US** (`us-contamination.yaml`, 21 now): + UST Finder releases (licence not stated), USACE FUDS (3), nonattainment (7).
- **Netherlands** (`vocab/seeds/nl-pollution.yaml`, keyword `nl-pollution-pack`, 7, all open): WKPB Wbb decisions (WBA)
  through **OGC API Features**, RIVM releases and drinking water zones (WFS), Zeeland and Noord-Holland landfills.
- **Australia** (`vocab/seeds/au-pollution.yaml`, keyword `au-pollution-pack`, 9): `nation` is the state. NSW licences and
  Tasmania aren't open (licence not stated / not specified). **NPI** hosted from its download
  (`vocab/files/au-npi-facilities.yaml`, keep-list drops names, ABN, addresses); it isn't in `files-monthly.env` yet:
  NPI updates once a year (by 31 March), so a refresh each April is enough (add it to the monthly list if that's easier).
- **Worker (atlas-mcp):** protocol `ogc-api-features` (with `info.query`, a fixed filter), and WFS/ArcGIS answers in a
  projected CRS now fail instead of returning metre coordinates (PDOK's MapServer WFS does this).
- **Licences:** `licences.recognise` (combine.py) re-reads `open_licence` with the fixed rule: licences given as URLs count,
  NC/ND don't. Upgrade-only except where NC/ND is named.
- **Still open, in order:**
  1. EU industrial emissions register: EEA's hosts didn't answer GitHub on 25 Nov, nor on 26 Nov (probe round 53:
     sdi.eea.europa.eu and industry.eea time out, discodata 502). Try a probe again; if the download
     answers (`sdi.eea.europa.eu/webdav/datastore/public/eea_v_4326_10_m_ied-eprtr_p_2007-2024_v15_r00/`), host it like the
     EA files (files.py would need a `layer` key for a multi-layer GeoPackage).
  2. NL: host PDOK's BRO soil decisions (SLD, CC0, WMS only as a service) from PDOK's download; Bodemloket has no service.
  3. Rob's calls: WA contaminated sites (custom licence), UK past land use (BGS 50k artificial ground: licence statements
     conflict), EA aquifer designations (no official service found), NSW licences and Tasmania (licence unread/unstated).
  4. Not found: Queensland EMR/CLR (not public), Defence PFAS areas (PDFs), US state cleanup lists (crawl copies only).

## Best in class and the fill wave (24 Nov, night)

Details in decisions.md (24 Nov, night).
- **Purpose (Rob):** the standout global and national sources (NASA, USGS, Copernicus, GEBCO, Geoscience Australia,
  BGS...) should lead broad searches. The registry's weekly list, sorted by number of services, surfaced volume
  (Brisbane City Council) instead. Agreed split:
  - **Trusted** (authoritative for its own data): to become mostly automatic (government or international body on its
    own domain or ArcGIS Online organisation); Rob reviews only odd cases. Not built yet.
  - **Best in class**: `vocab/best_in_class.yaml`, Rob's list. Not used by the pipeline yet; the plan is a ranking boost
    in broad searches and a `best_in_class` flag (contract note first), matched by host or organisation, never by name.
- Publisher issues #2-#13 stay **open** on purpose: closing one declines everything unticked, and open issues hold back
  the weekly lists. Rob has ticked 3 in #2 (Geoscience Australia, ONS, Institut Cartogràfic Valencià). Retire them when
  the automatic trusted rule is built.
- **Fill wave** (`vocab/seeds/fill.yaml`, `spike-fill`, last in publish order): 5,100 datasets, 463 passing, $0.03 to tag.
  Live checks: Met Office climate layers (its own organisation, credited "Met Office"), USGS National Map hydrography,
  NASA ARIA layers all come back through `find_datasets`; mcp-check passed.
- **Still thin, and the next steps:**
  - NASA GIBS: 2,884 layers, 1 with a description, so they fail the quality bar. Fix: join each layer to NASA's own text
    (`gibs.earthdata.nasa.gov/layer-metadata/v1.0/<layer>.json` lists its CMR `conceptIds`; CMR's collection `summary`
    is NASA's description). Reachable from GitHub (probe round 44).
  - Smithsonian GVP (399 WFS types, no descriptions; website blocks bots), SoilGrids depth layers, WRI: curated records
    for the few that matter, or leave.
  - Copernicus Marine: 84 MB capabilities, over the client's 30 MB cap (`max_bytes` in atlas/net.py).
  - GloFAS: 502 during the crawl only; rerun. USGS mineral resources (mrdata): robots.txt disallows.
  - Not found or refused: Bureau of Meteorology (403 to GitHub), KNMI (key), TNO/NLOG (no public service found),
    SEDAC geoserver (timeout), NASA NEO, World Bank map services. Copernicus Land comes via EEA; Terrascope blocks GitHub.

## Screening zones (26 Nov, evening)

Tobler's eight requests (project doc `claude/research-asset-reaches.md`, section 3). Contract note with ids and fields in
docs/mcp-tools.md (26 Nov evening); handback for Tobler in the project, `claude/screening-zones-atlas-handback-2026-11-26.md`.
- `vocab/seeds/screening-zones.yaml` (keyword `screening-zones-pack`, wave `spike-zones`): HSE consultation zones
  `a15122ad188c6d23`, Natura 2000 NL `9727d665d1fefb83` (OGC API), FEMA NFHL flood hazard zones `043582eb571bb87f`, EPA
  Sole Source Aquifers `00e494c4df69f701`. Tagged for under a cent. Live checks (mcp-ask, 21:24): all four open with
  `get_dataset`, the three data records return the right features (Nijkerk, Houston, Long Island).
- **New field `info.access: "restricted"`** (HSE): a record of data that exists but isn't published; landing only.
- FEMA's robots.txt disallows automated checks and it refuses GitHub's runners: since 27 Nov both endpoints carry
  `manual_check`, so the spike and sweep don't fetch it ("checked by hand", probe 54).
  Same footing as the EA flood zones. Never count the whole layer (it times out).
- IRZ decoding, England's SPZs and flood zones were already done; Victoria's catchments and extractive areas are crawled.
- **Texas and California (Rob's pick, late evening):** six TCEQ capture zone records (2, 5, 20, 50, 100 year, half-mile;
  `70c9684b9b239e17`, `6687b431d240e1c5`, `e33f7be1786fa951`, `b2ee5931a554b370`, `2aa46121508c506a`, `396d3904b71f7349`),
  licence not stated, TCEQ's robots.txt is "Disallow: /" (same footing as FEMA, Rob agreed). California: restricted record
  `b2617fec04a664c5` (no zone layer on the State Water Board's public server; well locations are public on GAMA).
  Spike run 2 lost FEMA to a transient connection refusal (it would have dropped out of the publish); run 3 put it back.
  If a curated host is down on a spike run, rerun before the publish settles.
- **Still open:** other US states' wellhead layers (crawled for MN, MA, OK, MI, DE, ND); RIVM Netkaart (data.rivm.nl/geo/nl didn't answer
  GitHub twice: retry with probe); in concept searches these records rank below local layers (Natura 2000 18th near Nijkerk,
  NFHL not in Houston's top 20) until best-in-class ranking is built. Not found as services: NL radar areas, Basisnet attention
  areas, Victoria wind exclusions, a UK aerodrome safeguarding layer (a few councils publish their own, licences unstated).

## Known gaps and next steps (rough priority)

1. **The OpenStreetMap copy:** UK (26 Nov) and NL (27 Nov) published, weekly, each in the atlas as a record; next AU
   (its section above).
   **Pollution screening:** next steps in its section above (EU register, BRO soil decisions, Rob's licence calls).
2. **Sweep retirements** are due from ~1 Dec: check nothing retires wrongly (curated endpoints fixed 26 Nov; shared ArcGIS
   Online hosts per organisation and FEMA checked by hand, 27 Nov). Check on 30 Nov that resolving is back near 99%. Expected real retirements:
   oceandata.rad.rutgers.edu, gis1.mgipu.hr, gis12.cookcountyil.gov. Watch the EEA discomap hosts (all down on 24 Nov).
3. **Best in class:** GIBS descriptions via CMR, then the ranking boost and flag (with the publisher registry stage 2
   release: `publisher_id`, `trusted`, `hosted_by`, `publisher_credit`, `trusted_only`, licence classes, one full reload;
   design in `docs/publisher-registry-design.md` and `docs/trusted-services-design.md`).
4. **US quality.**
   - Licences (17 Nov): Rob approved inferring public domain for US federal works (`atlas/licences.py`, labelled
     "inferred"). See `docs/us-licences.md`.
   - Still open: almost no US layers are joined to data.gov or Hub catalogue records (158 of 2,076 catalogues gave
     records). That join is the way to real licences for state and local data, and better US descriptions.
5. **Global source failures** (on their side): Terrascope (blocks cloud addresses), FAO io.apps GeoServer (502),
   UNEP-WCMC proxied ImageServers (token error), GFW tiles (robots.txt).
6. **Smaller items.**
   - The data's own date per record (`details.data_date`) is only on the curated UK records and hosted files; the sweep
     could read `editingInfo.lastEditDate` for crawled ArcGIS layers.
   - Offshore points still rank England-wide land layers above offshore records (bounding boxes; footprints would fix it).
   - ArcGIS layers that can't page (HES): `fetch_features` and the viewer retry without `resultRecordCount`; the viewer
     side still needs a look in a real browser.
   - Trim long credit strings used as publisher names (the fill wave adds more: "Contains Met Office data licensed...").
   - Add WMTS/WCS data checks. True footprints for false extents. An admin-area hierarchy.
   - Proposed new concepts: landscape-character-area, habitat-network, great-crested-newt-risk-zones. There is no
     wildfire, earthquake or volcano concept; the fill wave uses natural-hazard.
   - The viewer's header still says "Public map services from UK government and agencies" (public text: Rob's call).
   - Add a few UK pack records to mcp-check (a WFS one, HES, SEPA surface water, the IRZ).
   - Actions still run on Node 20 actions (checkout@v4 and friends), now forced onto Node 24 with a warning: bump them.
7. **Size limits.** GitHub Pages is capped at 1 GB; the site is ~203 MB (gzipped detail shards in `data/dz/`). A
   `size-limit` job fails at 800 MB. R2 (`atlas-data`, now in place) is the next step (`docs/viewer-data-size.md`). Not
   yet tested in Safari or Firefox.
8. **Actions concurrency.** The free plan runs 20 jobs at once; a 20-shard wave queues everything else (including the
   sweep) until shards finish. The osm workflow uses up to 6 build jobs (`MAX_PARALLEL`); its weekly crons are on
   Saturday and Sunday mornings, away from the crawl waves, which are started by hand.
9. **Africa.** 8,688 passing datasets under Rob's national-authority rule (a trial for Africa only; judge before
   extending it, `AUTHORITY_PASS_COUNTRIES` in quality.py). GNPC, Kenya's petroleum department and ANPG's ArcGIS Online
   need a token. Nigeria and Tanzania still need domain discovery (`docs/spikes/africa-scoping.md`).
10. **Tobler requests** (`docs/mcp-tools.md` has the log). Name index: waiting on Rob's licence call.
11. **Hosted download datasets** (`atlas/files.py`, specs `vocab/files/*.yaml`, wave `spike-files`): 18 GEM trackers
    (CC BY 4.0; some left out on licence grounds), JNCC offshore MPAs, NSIP, EA files. To refresh GEM: put the new file in
    a folder, update `source`/`release`/`citation`, run `python -m atlas.files --source-dir DIR vocab/files/<id>.yaml`,
    bump `runs/spike-files.env`, push. These could move to `atlas-data` too, when Pages fills up.
12. **Values at a point** (capability `sample`; `atlas/sampling.py`, `vocab/sample_rules.yaml`, wave `spike-values`).
    Open: shipping density from Esri's tiles-only copy (hosting the World Bank GeoTIFFs as a COG on R2 is Rob's call);
    GEBCO's OPeNDAP at CEDA is slow and sometimes 403; next elevation sources: LINZ 1 m COGs, other German states,
    Flanders WCS; Denmark, Finland, Sweden need keys. Add false-positive image services to `never` in sample_rules.yaml.
13. **UK pack follow-ups.** Read the James Hutton Institute Open Data Licence; read Historic England's Open Data Hub terms
    in a browser once. Gaps Tobler reports as "not checked": Dark Sky Parks, Scotland's Local Landscape Areas, Cadw
    battlefields, NI flood maps and farmland classification.
