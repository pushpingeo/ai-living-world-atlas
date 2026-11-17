# Viewer data and the 1 GB GitHub Pages limit: plan (17 Nov 2026)

**Done 17 Nov (A and B, Rob approved).** The site went from 702 MB to 203 MB: detail shards are now `data/dz/<first 3
characters>.json.gz` (4,096 files, 125 MB), unzipped in the browser, and a click fetches about 30 KB. `meta.json` names
the layout, and `app.js`/`style.css` are version-stamped at build. Tested in Chrome (desktop and phone size) locally and
checked on the live site; Safari and Firefox not tested. R2 (option C) stays in reserve.

## Where we are

- The site is **702 MB**: detail shards `data/d/` 628 MB (256 files, about 2.5 MB each), map tiles `data/t/` 72 MB,
  `big.json` 4 MB. It was ~560 MB before the 17 Nov Europe rerun.
- The `size-limit` job in `pages.yml` fails at 800 MB, so a GitHub failure email goes out. The deploy still runs.
- Clicking a dataset fetches its whole shard: 2.5 MB of JSON (about 0.5 MB over the wire with Pages' gzip) to
  show one record.

## Options

**A. Store the shards gzipped and unzip them in the browser (recommended first step).**
Write `d/xx.json.gz` and read it with the browser's built-in `DecompressionStream`. JSON like this shrinks about
5x: the whole 702 MB site zips to 126 MB in the Pages artifact. That would take the site to roughly 200 MB.
- Cost: nothing. No new service, no new secret.
- Work: about 20 lines across `viewer_data.py` and `app.js`. Test in Chrome, Firefox and Safari, desktop and phone
  (`DecompressionStream` needs Safari 16.4+, from 2023).
- Risk: low. Pages serves `.gz` as a plain file, so the browser won't double-decode it.
- Headroom: room for several more Europe-sized waves.

**B. More, smaller shards (4,096 by 3 hex characters).** Doesn't shrink the total, but a click fetches about 150 KB
instead of 2.5 MB. Worth doing alongside A because it makes the viewer feel quicker. File count goes from 1k to
about 5k, which is fine on Pages.

**C. Move the shards to Cloudflare R2.** A public bucket (r2.dev address or a subdomain) with CORS for the viewer.
- Cost: within R2's free allowance at this size (10 GB storage, 10M reads a month; no egress fees). Covered by the
  Workers Paid plan we already have.
- Work: the pages workflow uploads changed shards with wrangler (the backup workflow already writes to R2), and
  `app.js` points `d/` at the bucket.
- Risks: a second place the viewer depends on; a CORS or cache mistake breaks details while the map still works;
  making a bucket public is a step you'd want to approve.
- Only needed if A and B aren't enough, for example a much bigger world index.

**D. Serve details from the MCP Worker's D1.** The data is already there. But the MCP server is key-protected by
your rule, and opening a public read endpoint is a policy change. Not recommended unless you want a public API anyway.

## Suggestion

Do A and B together (half a day including browser tests), then keep R2 in reserve.
