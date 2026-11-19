"""Country spike: seeds -> portals -> services -> layers -> sample checks -> scores -> GeoParquet + report.

Usage: python -m atlas.spike --registry full.parquet --countries GB --out out/gb --minutes 150
"""
from __future__ import annotations

import argparse
import asyncio
import json
import pickle
import random
import re
import time
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd
from urllib.parse import urlsplit

from . import crawl_arcgis, crawl_ogc, endpoints, extents
from .datasets import build as build_datasets
from .crawl_portals import ogc_layer_key, harvest_arcgis_online, harvest_ckan, harvest_data_europa, harvest_geonetwork, harvest_hub, service_targets
from . import records as curated_records
from .net import Client
from .quality import codelike, declared_iso_themes, score
from .record import norm_url
from .resolution import derive
from .seeds import empty_targets, load_curated, load_targets, merge_targets


def is_agol(url: str) -> bool:
    return urlsplit(url).netloc.lower().endswith(".arcgis.com")


async def run(args):
    t0 = time.monotonic()
    deadline = t0 + args.minutes * 60
    reserve = min(20 * 60, args.minutes * 60 * 0.25)  # time kept back for checks and writing
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    log = []

    def note(msg):
        line = f"[{int(time.monotonic() - t0):>5}s] {msg}"
        print(line, flush=True)
        log.append(line)

    targets = load_targets(args.registry, args.countries) if args.countries else empty_targets()
    for path in args.seeds:
        targets = merge_targets(targets, load_curated(path))
    if args.shard:  # split work across parallel jobs by a stable hash of each target's URL
        import zlib

        i, n = (int(x) for x in args.shard.split("/"))
        keep = lambda u: zlib.crc32(u.encode()) % n == i
        # GeoNetwork catalogues are harvested by every shard; the services they list are split later
        for k in ("arcgis_roots", "arcgis_services", "wms", "wfs", "wmts", "wcs", "hub", "ckan", "agol"):
            targets[k] = {u: v for u, v in targets[k].items() if keep(u)}
        if i != 0:
            targets["records"] = []
        note(f"shard {i}/{n}")
    shard_keep = (lambda u: True)
    if args.shard:
        shard_keep = keep
    if args.host_filter:  # for local testing: keep only targets on matching hosts
        rx = re.compile(args.host_filter)
        for k in ("arcgis_roots", "wms", "wfs", "wmts", "wcs", "hub", "ckan"):
            targets[k] = {u: v for u, v in targets[k].items() if rx.search(urlsplit(u).netloc)}
    note(f"seeds: { {k: (len(v) if isinstance(v, dict) else v) for k, v in targets.items() if k != 'used_by_software'} }")

    async with Client(total=args.concurrency, per_host=2) as c:
        # ---- 1. portals ---------------------------------------------------
        portal_status, records = [], []
        async def safe(coro, portal, kind):
            try:
                return await coro
            except Exception as e:
                return [], {"portal": portal, "kind": kind, "ok": False, "error": f"crash: {type(e).__name__}: {e}"[:200], "records": 0}
        jobs = [safe(harvest_hub(c, u, ctx["discovered_via"]), ctx["discovered_via"], "hub") for u, ctx in targets["hub"].items()]
        jobs += [safe(harvest_ckan(c, u, ctx["portal"], max_records=args.ckan_max), ctx["portal"], "ckan") for u, ctx in targets["ckan"].items()]
        jobs += [safe(harvest_arcgis_online(c, q, ctx["discovered_via"]), ctx["discovered_via"], "arcgis-online") for q, ctx in targets["agol"].items()]
        def gn_job(u, ctx):
            if ctx.get("api") == "data-europa":
                return harvest_data_europa(c, u, ctx["discovered_via"], deadline=t0 + args.minutes * 60 * (0.95 if args.harvest_only else 0.6))
            return harvest_geonetwork(c, u, ctx["discovered_via"])
        cached = None
        if args.portal_cache and Path(args.portal_cache).exists():
            cached = pickle.loads(Path(args.portal_cache).read_bytes())  # written by --harvest-only in the same workflow run
            note(f"portal cache: {len(cached['records'])} records from {len(cached['status'])} catalogues")
        if cached is None:
            jobs += [safe(gn_job(u, ctx), ctx["discovered_via"], ctx.get("api", "geonetwork")) for u, ctx in targets["gn"].items()]
        portal_ctx = {ctx["discovered_via"].split(":", 1)[1] if ctx["discovered_via"].startswith("hub:") else ctx["portal"]: ctx
                      for ctx in list(targets["hub"].values()) + list(targets["ckan"].values())}
        portal_ctx.update({ctx["discovered_via"]: ctx for ctx in list(targets["agol"].values()) + list(targets["gn"].values())})
        for coro in asyncio.as_completed(jobs):
            recs, st = await coro
            portal_status.append(st)
            records += recs
        if cached is not None:
            portal_status += cached["status"]
            records += cached["records"]
        if args.harvest_only:
            Path(args.harvest_only).parent.mkdir(parents=True, exist_ok=True)
            gn = [r for r in records if r.portal.startswith("gn:")]
            Path(args.harvest_only).write_bytes(pickle.dumps({"records": gn, "status": [s for s in portal_status if s.get("kind") in ("geonetwork", "data-europa")]}))
            note(f"harvest-only: wrote {len(gn)} catalogue records to {args.harvest_only}")
            for s_ in portal_status:
                note(f"  {s_.get('portal')}: ok={s_.get('ok')} records={s_.get('records')} scanned={s_.get('scanned')} {s_.get('error','')}")
            return
        note(f"portals: {sum(s['ok'] for s in portal_status)}/{len(portal_status)} ok, {len(records)} records with service links")

        # ---- 2. work out which services to crawl ----------------------------
        arc_roots = dict(targets["arcgis_roots"])
        arc_services: dict[str, dict] = dict(targets["arcgis_services"])
        ogc: dict[tuple[str, str], dict] = {(u, "WMS"): ctx for u, ctx in targets["wms"].items()}
        ogc.update({(u, "WFS"): ctx for u, ctx in targets["wfs"].items()})
        ogc.update({(u, "WMTS"): ctx for u, ctx in targets["wmts"].items()})
        ogc.update({(u, "WCS"): ctx for u, ctx in targets["wcs"].items()})
        for rec in records:
            pkey = rec.portal.split(":", 1)[1] if rec.portal.startswith("hub:") else rec.portal
            pctx = portal_ctx.get(pkey, {})
            agol = rec.portal.startswith(("agol:", "gn:"))
            ctx = {
                "publisher": rec.publisher or pctx.get("publisher", ""),
                # a CKAN aggregator's owner is not the data publisher; leave type to domain rules
                "publisher_type": pctx.get("publisher_type", "unknown") if (rec.portal.startswith("hub:") or agol) else "unknown",
                "country": getattr(rec, "country", "") or pctx.get("country", args.countries[0] if args.countries else ""), "seed_catalog": pctx.get("seed_catalog", ""),
                "discovered_via": rec.portal if (rec.portal.startswith("hub:") or agol) else f"ckan:{rec.portal}",
            }
            for kind, u in service_targets(rec):
                if rec.portal.startswith("gn:") and not shard_keep(u):
                    continue  # another shard crawls this one
                ctx_u = ctx
                if rec.portal.startswith("hub:") and not is_agol(u):
                    # a Hub listing a service on someone else's server: the Hub's owner isn't the publisher
                    ctx_u = {**ctx, "publisher": "", "publisher_type": "unknown", "listed_by": ctx["publisher"]}
                if kind == "arcgis-service":
                    arc_services.setdefault(u, ctx_u)
                    if not is_agol(u) and args.expand_roots:
                        root = crawl_arcgis.services_root(u)
                        if root:
                            arc_roots.setdefault(root, ctx_u)
                elif kind == "arcgis-root":
                    if not is_agol(u):
                        arc_roots.setdefault(u, ctx_u)
                elif kind in ("wms", "wfs", "wmts", "wcs"):
                    ogc.setdefault((u, kind.upper()), ctx_u)
        note(f"targets: {len(arc_roots)} ArcGIS roots, {len(arc_services)} ArcGIS services from portals, {len(ogc)} OGC endpoints")

        # ---- 3. list services under ArcGIS roots ----------------------------
        root_status = []
        async def list_root(root, ctx):
            try:
                svcs, info = await crawl_arcgis.list_services(c, root, max_services=args.max_services_per_root)
            except Exception as e:
                svcs, info = [], {"root": root, "status": None, "error": f"crash: {type(e).__name__}: {e}"[:200]}
            info["n_services"] = len(svcs)
            root_status.append(info)
            for s in svcs:
                arc_services.setdefault(s, ctx)
        await asyncio.gather(*[list_root(r, ctx) for r, ctx in arc_roots.items()])
        note(f"ArcGIS roots listed: {sum(1 for r in root_status if r['status'] == 200)}/{len(root_status)} reachable; {len(arc_services)} ArcGIS services total")

        # ---- 4. crawl services (time-boxed) ---------------------------------
        layers, svc_status = [], []
        work = [("arc", u, None, ctx) for u, ctx in arc_services.items()] + [("ogc", u, s, ctx) for (u, s), ctx in ogc.items()]
        random.Random(1).shuffle(work)  # spread load across hosts
        if args.max_services:
            work = work[: args.max_services]

        async def one(kind, u, s, ctx):
            if time.monotonic() > deadline - reserve:  # keep time for checks + writing
                svc_status.append({"service_url": u, "service_type": s or "arcgis", "ok": False, "error": "skipped: time budget", "n_layers": 0, "ms": 0})
                return
            try:
                if kind == "arc":
                    ls, st = await crawl_arcgis.crawl_service(c, u, ctx)
                else:
                    ls, st = await crawl_ogc.crawl_ogc(c, u, s, ctx)
            except Exception as e:
                ls, st = [], {"service_url": u, "service_type": s or "arcgis", "ok": False, "error": f"crash: {type(e).__name__}: {e}"[:200], "n_layers": 0, "ms": 0}
            layers.extend(ls)
            svc_status.append(st)

        done = 0
        for chunk_start in range(0, len(work), 500):
            await asyncio.gather(*[one(*w) for w in work[chunk_start:chunk_start + 500]])
            done += len(work[chunk_start:chunk_start + 500])
            note(f"services crawled {done}/{len(work)}; layers so far {len(layers)}")

        # ---- 4a. curated download-only records -----------------------------
        rec_layers = curated_records.to_layers(targets["records"])
        layers.extend(rec_layers)
        note(f"curated records: {len(rec_layers)} endpoints")

        # ---- 4b. false extents: flag, then measure what we can -------------
        extents.flag(layers)
        ext_stats = await extents.measure(c, layers, args.max_extent_checks, lambda: time.monotonic() < deadline - reserve / 2)
        note(f"extents: {ext_stats}")

        # ---- 5. attach catalogue metadata -----------------------------------
        # Only attach a catalogue record where it clearly describes this layer:
        #   - it links this exact layer, or
        #   - it links the whole service and the service is small (<= 3 layers) or the titles match.
        # A record linking one layer of a big service must not lend its description to the others.
        exact, whole = defaultdict(list), defaultdict(list)
        for rec in records:
            for kind, u in rec.links:
                nu = norm_url(u)
                if kind == "arcgis" and crawl_arcgis.service_url_of(u) and norm_url(crawl_arcgis.service_url_of(u)) != nu:
                    exact[nu].append(rec)          # .../MapServer/12: one layer
                elif kind == "arcgis":
                    whole[nu].append(rec)          # .../MapServer: the whole service
                else:
                    whole[nu].append(rec)          # OGC endpoint: the whole service
        named = defaultdict(list)  # records that name an OGC layer: matched on server and layer name
        for rec in records:
            for key in getattr(rec, "layer_names", None) or []:
                named[tuple(key)].append(rec)
        svc_size = Counter(L.service_url for L in layers)

        def same_title(r, L):
            a, b = (r.title or "").lower().strip(), (L.title or "").lower().strip()
            return bool(a and b and (a == b or a.replace("_", " ") == b.replace("_", " ")))

        joined = 0
        for L in layers:
            recs = exact.get(norm_url(L.layer_url), [])
            if not recs and L.service_type in ("wms", "wfs", "wmts", "wcs"):
                recs = named.get(ogc_layer_key(L.service_url, L.layer_name), [])
            if not recs:
                cands = whole.get(norm_url(L.service_url), [])
                titled = [r for r in cands if same_title(r, L)]
                recs = titled or (cands if svc_size[L.service_url] <= 3 and len(cands) == 1 else [])
            if recs:
                r = recs[0]
                L.portal_title, L.portal_abstract, L.portal_licence = r.title, r.abstract, r.licence
                L.stated_scale = getattr(r, "scale", None)
                L.landing_page = r.landing_page
                L.declared_themes = r.themes
                if not L.listed_by:
                    L.publisher = L.publisher or r.publisher
                joined += 1
        note(f"layers joined to a catalogue record: {joined}/{len(layers)}")

        # ---- 6. sample liveness checks ---------------------------------------
        per_svc = defaultdict(list)
        for L in layers:
            per_svc[L.service_url].append(L)
        sample = []
        rnd = random.Random(2)
        for s, ls in per_svc.items():
            sample += rnd.sample(ls, min(2, len(ls)))
        rnd.shuffle(sample)
        sample = sample[: args.max_checks]
        checks = {}

        async def chk(L):
            if time.monotonic() > deadline - reserve / 4:
                return
            fn = (crawl_ogc.check_layer if L.service_type in ("wms", "wfs", "wmts", "wcs")
                  else curated_records.check if (L.uid in curated_records.CHECK_URL or L.service_type in curated_records.CAPS)
                  else crawl_arcgis.check_layer)
            try:
                checks[L.uid] = await fn(c, L)
            except Exception as e:
                checks[L.uid] = ("fail", f"{type(e).__name__}")
        await asyncio.gather(*[chk(L) for L in sample])
        note(f"checks run: {len(checks)} (sampled {len(sample)})")
        http_stats = dict(c.stats)

    # ---- 7. score + write --------------------------------------------------
    svc_n = Counter(L.service_url for L in layers)
    rows = []
    for L in layers:
        r = L.to_row()
        st, detail = checks.get(L.uid, ("unchecked", ""))
        r["check_status"], r["check_detail"] = st, detail
        r["service_layer_count"] = svc_n[L.service_url]
        if not r["publisher"]:
            host = urlsplit(L.service_url).netloc.lower()
            words = [w for w in re.findall(r"[a-z]{4,}", (L.listed_by or "").lower())
                     if w not in {"city", "council", "county", "borough", "district", "government", "national", "authority", "agency", "metropolitan", "trust"}]
            # the lister's own server (e.g. Bristol City Council's Hub linking maps2.bristol.gov.uk) is fair to attribute
            r["publisher"] = L.listed_by if words and any(w in host for w in words) else host
        themes, how = declared_iso_themes(r["declared_themes"], r["keywords"])
        r["iso_themes_declared"], r["iso_themes_how"] = themes, how
        r.update(score(r))
        r.update(derive(r))
        r["role"] = endpoints.role({**r, "_info": json.loads(r["endpoint_info"] or "{}")})
        rows.append(r)
    dedup = {}
    for r in rows:  # first row wins; same uid can appear via two discovery routes
        dedup.setdefault(r["uid"], r)
    rows = list(dedup.values())
    note(f"unique layers: {len(rows)}")
    write_outputs(out, rows, svc_status, root_status, portal_status, http_stats, log, args, time.monotonic() - t0)


def _to_geo(df, bbox_col):
    import geopandas as gpd
    from shapely.geometry import box

    geom = [box(*b) if isinstance(b, (list, tuple)) and len(b) == 4 else None for b in df[bbox_col]]
    return gpd.GeoDataFrame(df.drop(columns=[bbox_col]), geometry=geom, crs="EPSG:4326")


def write_outputs(out: Path, rows, svc_status, root_status, portal_status, http_stats, log, args, secs):
    import pandas as pd

    from .quality import authority_pass
    rows = [authority_pass(dict(r)) for r in rows]  # rows scored by older code (remerge) get the current rule
    df = pd.DataFrame(rows)
    ds = pd.DataFrame()
    if len(df):
        for col in ("keywords", "fields", "declared_themes", "iso_themes_declared", "q_flags", "capabilities", "extent_flags"):
            df[col] = df[col].apply(lambda v: list(v) if isinstance(v, (list, tuple)) else [])
        df["_bbox"] = df["bbox"]
        t = time.monotonic()
        df, ds = build_datasets(df)
        log.append(f"datasets built in {time.monotonic() - t:.0f}s: {len(ds)} from {len(df)} endpoints")
        _to_geo(df.drop(columns=["_bbox"]), "bbox").to_parquet(out / "layers.parquet", write_covering_bbox=True, compression="zstd")
        _to_geo(ds, "_bbox").to_parquet(out / "datasets.parquet", write_covering_bbox=True, compression="zstd")
    pd.DataFrame(svc_status).to_parquet(out / "services.parquet")
    (out / "portals.json").write_text(json.dumps(portal_status, indent=1, default=str))
    (out / "roots.json").write_text(json.dumps(root_status, indent=1, default=str))
    (out / "run.log").write_text("\n".join(log))
    stats = summarise(df, svc_status, root_status, portal_status, http_stats, secs, out)
    if len(ds):
        stats["datasets"] = {
            "total": len(ds), "passing": int(ds["q_pass"].sum()),
            "endpoints_per_dataset": ds["n_endpoints"].value_counts().sort_index().head(10).to_dict(),
            "multi_protocol": int((ds["protocols"].apply(len) > 1).sum()),
            "match_rules": pd.Series([r for rs in ds["match_rules"] for r in rs]).value_counts().to_dict(),
            "role": ds["role"].value_counts().to_dict(),
            "role_passing": ds.loc[ds["q_pass"], "role"].value_counts().to_dict(),
            "capabilities": pd.Series([c for cs in ds["capabilities"] for c in cs]).value_counts().to_dict(),
            "detail_known_passing": int(ds.loc[ds["q_pass"], "detail_m"].notna().sum()),
        }
        (out / "stats.json").write_text(json.dumps(stats, indent=1, default=str))
    (out / "stats.json").write_text(json.dumps(stats, indent=1, default=str))
    (out / "REPORT.md").write_text(report_md(stats, args))


def summarise(df, svc_status, root_status, portal_status, http_stats, secs, out):
    s = {"minutes": round(secs / 60, 1), "http": http_stats}
    s["portals"] = {"total": len(portal_status), "ok": sum(p["ok"] for p in portal_status),
                    "records_with_service_links": sum(p.get("records", 0) for p in portal_status)}
    s["arcgis_roots"] = {"total": len(root_status), "reachable": sum(1 for r in root_status if r.get("status") == 200)}
    s["services"] = {"attempted": len(svc_status), "ok": sum(1 for x in svc_status if x["ok"]),
                     "skipped_time": sum(1 for x in svc_status if str(x.get("error", "")).startswith("skipped")),
                     "by_type": dict(Counter(x["service_type"] for x in svc_status if x["ok"])),
                     "top_errors": Counter(re.sub(r"\d{3,}", "N", str(x.get("error", ""))[:60]) for x in svc_status if not x["ok"]).most_common(8)}
    if not len(df):
        return s
    n = len(df)
    chk = df["check_status"].value_counts().to_dict()
    checked = chk.get("ok", 0) + chk.get("fail", 0) + chk.get("empty", 0)
    s["layers"] = {
        "total": n, "by_service_type": df["service_type"].value_counts().to_dict(),
        "with_bbox": int(df["bbox"].notna().sum()),
        "with_abstract_50": int((df["q_abstract_len"] >= 50).sum()),
        "with_licence_text": int(((df["licence_text"].str.len() > 0) | (df["portal_licence"].str.len() > 0)).sum()),
        "with_open_licence": int(df["q_open_licence"].sum()),
        "with_keywords": int(df["keywords"].apply(len).gt(0).sum()),
        "joined_to_catalogue": int((df["portal_title"].str.len() > 0).sum()),
        "codelike_titles": int(df["title"].apply(codelike).sum()),
        "junk_flagged": int(df["q_flags"].apply(len).gt(0).sum()),
        "declared_iso_theme": int(df["iso_themes_declared"].apply(len).gt(0).sum()),
        "declared_theme_how": df["iso_themes_how"].replace("", "none").value_counts().to_dict(),
        "publisher_type": df["publisher_type_resolved"].value_counts().to_dict(),
        "detail_source": df["detail_source"].replace("", "none").value_counts().to_dict(),
        "extent_source": df["extent_source"].value_counts().to_dict(),
        "extent_flags": pd.Series([f for fs in df["extent_flags"] for f in fs]).value_counts().to_dict(),
        "cors_ok": int(df["cors"].fillna(False).astype(bool).sum()),
        "detail_level": df["detail_level"].replace("", "unknown").value_counts().to_dict(),
        "coverage_level": df["coverage_level"].replace("", "unknown").value_counts().to_dict(),
        "detail_level_passing": df.loc[df["q_pass"], "detail_level"].replace("", "unknown").value_counts().to_dict(),
    }
    s["checks"] = {"by_status": chk, "live_rate_of_checked": round(chk.get("ok", 0) / checked, 3) if checked else None,
                   "returns_data_or_empty_rate": round((chk.get("ok", 0) + chk.get("empty", 0)) / checked, 3) if checked else None}
    s["quality"] = {"pass": int(df["q_pass"].sum()), "pass_rate": round(float(df["q_pass"].mean()), 3),
                    "score_median": float(df["q_total"].median()),
                    "score_bands": pd_bands(df["q_total"])}
    key = df["title"].str.lower().str.strip() + "|" + df["publisher"].str.lower().str.strip()
    s["dedupe"] = {"distinct_title_publisher": int(key.nunique()),
                   "distinct_among_passing": int(key[df["q_pass"]].nunique())}
    f = out / "layers.parquet"
    s["file_mb"] = round(f.stat().st_size / 1e6, 2) if f.exists() else None
    return s


def pd_bands(series):
    import pandas as pd

    return pd.cut(series, [0, 40, 50, 60, 70, 80, 101], right=False).astype(str).value_counts().sort_index().to_dict()


def report_md(s, args):
    L = s.get("layers", {})
    q = s.get("quality", {})
    ck = s.get("checks", {})

    def pct(a, b):
        return f"{100 * a / b:.0f}%" if b else "n/a"

    n = L.get("total", 0)
    lines = [
        f"# Spike report: {','.join(args.countries) or 'curated seeds'}{' + ' + ', '.join(args.seeds) if args.seeds else ''}",
        "",
        f"Run time {s['minutes']} min; {s['http']['requests']} HTTP requests; {s['http'].get('robots_blocked', 0)} blocked by robots.txt.",
        "",
        "## Coverage",
        f"- Catalogues harvested: {s['portals']['ok']}/{s['portals']['total']} (records linking to services: {s['portals']['records_with_service_links']})",
        f"- ArcGIS server roots reachable: {s['arcgis_roots']['reachable']}/{s['arcgis_roots']['total']}",
        f"- Services crawled OK: {s['services']['ok']}/{s['services']['attempted']} (skipped for time: {s['services']['skipped_time']}); by type {s['services']['by_type']}",
        f"- **Layers found: {n}** ({L.get('by_service_type')})",
        f"- Distinct title+publisher (rough dedupe): {s.get('dedupe', {}).get('distinct_title_publisher')}",
        "",
        "## Metadata quality",
        f"- Abstract of 50+ chars: {pct(L.get('with_abstract_50', 0), n)}",
        f"- Any licence/constraints text: {pct(L.get('with_licence_text', 0), n)}; recognised open licence: {pct(L.get('with_open_licence', 0), n)}",
        f"- Keywords: {pct(L.get('with_keywords', 0), n)}; WGS84 extent: {pct(L.get('with_bbox', 0), n)}",
        f"- Linked to a catalogue record: {pct(L.get('joined_to_catalogue', 0), n)}",
        f"- Code-like layer titles (before using catalogue names): {pct(L.get('codelike_titles', 0), n)}; junk-flagged: {pct(L.get('junk_flagged', 0), n)}",
        f"- **Declares an ISO theme (directly or via INSPIRE/DGU crosswalk): {pct(L.get('declared_iso_theme', 0), n)}** {L.get('declared_theme_how')}",
        f"- Publisher type: {L.get('publisher_type')}",
        "",
        "## Datasets (endpoints grouped)",
        f"- **Datasets: {s.get('datasets', {}).get('total')}** from {n} endpoints; passing: {s.get('datasets', {}).get('passing')}",
        f"- Reachable by more than one protocol: {s.get('datasets', {}).get('multi_protocol')}",
        f"- Endpoints per dataset: {s.get('datasets', {}).get('endpoints_per_dataset')}",
        f"- Grouping rules used: {s.get('datasets', {}).get('match_rules')}",
        f"- Role (all / passing): {s.get('datasets', {}).get('role')} / {s.get('datasets', {}).get('role_passing')}",
        f"- Capabilities offered: {s.get('datasets', {}).get('capabilities')}",
        "",
        "## Coverage and detail",
        f"- Coverage level (from extent): {L.get('coverage_level')}",
        f"- Extent source: {L.get('extent_source')}; suspect-extent flags: {L.get('extent_flags')}",
        f"- Endpoints that allow browser access (CORS): {L.get('cors_ok')}",
        f"- Detail estimate source: {L.get('detail_source')}",
        f"- Detail level, all layers: {L.get('detail_level')}",
        f"- Detail level, passing layers: {L.get('detail_level_passing')}",
        "",
        "## Liveness (sample, up to 2 layers per service)",
        f"- {ck.get('by_status')}",
        f"- Returns data: {ck.get('live_rate_of_checked')}; returns data or valid empty: {ck.get('returns_data_or_empty_rate')}",
        "",
        "## Quality bar",
        f"- **Pass: {q.get('pass')} layers ({100 * (q.get('pass_rate') or 0):.0f}%)**; distinct among passing: {s.get('dedupe', {}).get('distinct_among_passing')}",
        f"- Score median {q.get('score_median')}; bands {q.get('score_bands')}",
        "",
        "## Size",
        f"- layers.parquet: {s.get('file_mb')} MB for {n} layers",
        "",
        "## Top service errors",
        *[f"- {e or '(none)'}: {k}" for e, k in s["services"]["top_errors"]],
        "",
        "AI-tag agreement is not in this run (needs the API key); it comes next.",
    ]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", required=True)
    ap.add_argument("--countries", default="GB", help="comma list of ISO2 codes from the registry; empty for none")
    ap.add_argument("--seeds", action="append", default=[], help="curated seed file(s), e.g. vocab/seeds/global.yaml")
    ap.add_argument("--out", default="out/gb")
    ap.add_argument("--minutes", type=float, default=150)
    ap.add_argument("--concurrency", type=int, default=48)
    ap.add_argument("--ckan-max", type=int, default=100_000)
    ap.add_argument("--max-services", type=int, default=0)
    ap.add_argument("--max-services-per-root", type=int, default=1500)
    ap.add_argument("--max-checks", type=int, default=4000)
    ap.add_argument("--max-extent-checks", type=int, default=15000)
    ap.add_argument("--host-filter", default="")
    ap.add_argument("--portal-cache", default="", help="pickle of catalogue records from a --harvest-only run")
    ap.add_argument("--harvest-only", default="", help="harvest the big catalogues (GeoNetwork, data.europa.eu), write a pickle here, stop")
    ap.add_argument("--shard", default="", help="i/n: crawl only the i-th of n slices of the seed targets")
    ap.add_argument("--expand-roots", action="store_true", default=True)
    args = ap.parse_args()
    args.countries = [c.strip().upper() for c in args.countries.split(",") if c.strip()]
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
