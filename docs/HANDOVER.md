# AI Living World Atlas: handover (16 Nov 2026)

Start here when picking the atlas up in a new chat. The detailed history of decisions is in `docs/decisions.md`.

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
| Tags | `results/tags-<wave>` |
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
| `spike` | `runs/spike-<wave>.env` | Crawls a wave in parallel shards, then merges. Settings: `PREHARVEST=1` harvests big catalogues once; `CONCAT=1` merges without regrouping, for very large waves. |
| `remerge` | `runs/remerge.env` | Redoes only the merge from an earlier run's shard artifacts (kept 7 days). |
| `collections` | `runs/collections.env` | Groups local development plans into one dataset per council. Europe is derived this way: `spike-inspire` becomes `spike-europe`. |
| `tag` | `runs/tag-<wave>.env` | Haiku 5.5 tagging through the Batch API. Splits into several batches, skips datasets already tagged, and writes `COST.md`. To resume, set `BATCH_ID=id1,id2,...`. |
| `backup` | automatic | Runs after every tag run. |
| `pages` | automatic | Rebuilds the viewer from the waves listed in `runs/published.txt`. Passing datasets only. |
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
| Europe (`spike-europe`) | 1.64M | 73.7k | From data.europa.eu, since the INSPIRE geoportal has gone; 488k local plans grouped into 1,672 council collections |

- The viewer and the MCP server hold about **212k passing datasets**, all tagged.
- Tagging spend is **$23.86** in total: UK $4.76 (including the quality check), global $1.14, CANZ $5.08, US $6.39, Europe $6.49.
- At batch rates, tagging costs about **$0.09 per 1,000 datasets**.

## Rules Rob set

- Keep the MCP server key-protected.
- Report API costs as they happen, and ask before any tagging run over about $20.
- Ask before big or hard-to-undo choices. Otherwise make a sensible call and say so.
- Test properly, including in the browser, and say plainly what was and wasn't tested.
- Anything public must read as if a person wrote it.
- Keep Rob's involvement minimal.

## Known gaps and next steps (rough priority)

1. **Rolling liveness sweep.** Recheck services on a schedule (target ~98% resolving), cheaply.
   - Only re-tag datasets whose description changed.
   - Retire dead services.
   - Nothing is scheduled yet.
2. **Europe harvest was partial.** data.europa.eu returned bad scroll pages, so the harvest got 367k of about 880k
   catalogue records: WMS stopped at 158k of 516k and WFS at 211k of 366k. The harvester now retries those pages.
   - Rerun `spike-inspire`, then `collections`, then tag the new datasets only.
   - Watch the Europe merge memory; `CONCAT=1` is set for this wave.
3. **US quality.**
   - Licence detection doesn't recognise "public domain" wording, so no US licence is marked open.
   - Almost no US layers are joined to data.gov or Hub catalogue records (158 of 2,076 catalogues gave records).
4. **Global source failures.**
   - Terrascope: connection reset.
   - FAO map server: 502.
   - GFW tiles: blocked by robots.txt.
   - Some UNEP-WCMC proxied ImageServers.
5. **Smaller items.**
   - Trim long credit strings used as publisher names.
   - Add WMTS/WCS liveness checks.
   - Work out true footprints for false extents (they are currently only flagged and ranked down).
   - Add an admin-area hierarchy.
   - Proposed new concepts: landscape-character-area, habitat-network, great-crested-newt-risk-zones.
6. **Tobler integration.** Wire the MCP server into Tobler as a data source.
7. **Size limits.** GitHub Pages is capped at 1 GB, and the viewer data is about 560 MB. If more waves push it over,
   move the viewer data to R2.
