"""Country spike: seeds -> portals -> services -> layers -> sample checks -> scores -> GeoParquet + report.

Usage: python -m atlas.spike --registry full.parquet --countries GB --out out/gb --minutes 150
"""
from __future__ import annotations

import argparse
import asyncio
import json
import random
import re
import time
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlsplit

from . import crawl_arcgis, crawl_ogc
from .crawl_portals import harvest_ckan, harvest_hub, service_targets
from .net import Client
from .quality import codelike, declared_iso_themes, score
from .record import norm_url
from .seeds import load_targets


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

    targets = load_targets(args.registry, args.countries)
    if args.host_filter:  # for local testing: keep only targets on matching hosts
        rx = re.compile(args.host_filter)
        for k in ("arcgis_roots", "wms", "wfs", "hub", "ckan"):
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
        portal_ctx = {ctx["discovered_via"].split(":", 1)[1] if ctx["discovered_via"].startswith("hub:") else ctx["portal"]: ctx
                      for ctx in list(targets["hub"].values()) + list(targets["ckan"].values())}
        for coro in asyncio.as_completed(jobs):
            recs, st = await coro
            portal_status.append(st)
            records += recs
        note(f"portals: {sum(s['ok'] for s in portal_status)}/{len(portal_status)} ok, {len(records)} records with service links")

        # ---- 2. work out which services to crawl ----------------------------
        arc_roots = dict(targets["arcgis_roots"])
        arc_services: dict[str, dict] = {}
        ogc: dict[tuple[str, str], dict] = {(u, "WMS"): ctx for u, ctx in targets["wms"].items()}
        ogc.update({(u, "WFS"): ctx for u, ctx in targets["wfs"].items()})
        for rec in records:
            pkey = rec.portal.split(":", 1)[1] if rec.portal.startswith("hub:") else rec.portal
            pctx = portal_ctx.get(pkey, {})
            ctx = {
                "publisher": rec.publisher or pctx.get("publisher", ""),
                # a CKAN aggregator's owner is not the data publisher; leave type to domain rules
                "publisher_type": pctx.get("publisher_type", "unknown") if rec.portal.startswith("hub:") else "unknown",
                "country": pctx.get("country", args.countries[0]), "seed_catalog": pctx.get("seed_catalog", ""),
                "discovered_via": rec.portal if rec.portal.startswith("hub:") else f"ckan:{rec.portal}",
            }
            for kind, u in service_targets(rec):
                if kind == "arcgis-service":
                    arc_services.setdefault(u, ctx)
                    if not is_agol(u) and args.expand_roots:
                        root = crawl_arcgis.services_root(u)
                        if root:
                            arc_roots.setdefault(root, ctx)
                elif kind == "arcgis-root":
                    if not is_agol(u):
                        arc_roots.setdefault(u, ctx)
                elif kind in ("wms", "wfs"):
                    ogc.setdefault((u, kind.upper()), ctx)
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

        # ---- 5. attach catalogue metadata -----------------------------------
        by_url = defaultdict(list)
        for rec in records:
            for kind, u in rec.links:
                by_url[norm_url(u)].append(rec)
                if kind == "arcgis":
                    s = crawl_arcgis.service_url_of(u)
                    if s:
                        by_url[norm_url(s)].append(rec)
        joined = 0
        for L in layers:
            recs = by_url.get(norm_url(L.layer_url)) or by_url.get(norm_url(L.service_url)) or []
            if L.service_type in ("wms", "wfs") and len(recs) > 1:
                # many datasets share one OGC endpoint: only keep a record whose title matches the layer
                recs = [r for r in recs if r.title and L.title and r.title.lower() == L.title.lower()]
            if recs:
                r = recs[0]
                L.portal_title, L.portal_abstract, L.portal_licence = r.title, r.abstract, r.licence
                L.landing_page = r.landing_page
                L.declared_themes = r.themes
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
            fn = crawl_ogc.check_layer if L.service_type in ("wms", "wfs") else crawl_arcgis.check_layer
            try:
                checks[L.uid] = await fn(c, L)
            except Exception as e:
                checks[L.uid] = ("fail", f"{type(e).__name__}")
        await asyncio.gather(*[chk(L) for L in sample])
        note(f"checks run: {len(checks)} (sampled {len(sample)})")
        http_stats = dict(c.stats)

    # ---- 7. score + write --------------------------------------------------
    rows = []
    for L in layers:
        r = L.to_row()
        st, detail = checks.get(L.uid, ("unchecked", ""))
        r["check_status"], r["check_detail"] = st, detail
        themes, how = declared_iso_themes(r["declared_themes"], r["keywords"])
        r["iso_themes_declared"], r["iso_themes_how"] = themes, how
        r.update(score(r))
        rows.append(r)
    dedup = {}
    for r in rows:  # first row wins; same uid can appear via two discovery routes
        dedup.setdefault(r["uid"], r)
    rows = list(dedup.values())
    note(f"unique layers: {len(rows)}")
    write_outputs(out, rows, svc_status, root_status, portal_status, http_stats, log, args, time.monotonic() - t0)


def write_outputs(out: Path, rows, svc_status, root_status, portal_status, http_stats, log, args, secs):
    import geopandas as gpd
    import pandas as pd
    from shapely.geometry import box

    df = pd.DataFrame(rows)
    if len(df):
        geom = [box(*b) if isinstance(b, list) and len(b) == 4 else None for b in df["bbox"]]
        gdf = gpd.GeoDataFrame(df.drop(columns=["bbox"]), geometry=geom, crs="EPSG:4326")
        for col in ("keywords", "fields", "declared_themes", "iso_themes_declared", "q_flags"):
            gdf[col] = gdf[col].apply(lambda v: list(v) if isinstance(v, (list, tuple)) else [])
        gdf.to_parquet(out / "layers.parquet", write_covering_bbox=True, compression="zstd")
    pd.DataFrame(svc_status).to_parquet(out / "services.parquet")
    (out / "portals.json").write_text(json.dumps(portal_status, indent=1, default=str))
    (out / "roots.json").write_text(json.dumps(root_status, indent=1, default=str))
    (out / "run.log").write_text("\n".join(log))
    stats = summarise(df, svc_status, root_status, portal_status, http_stats, secs, out)
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
        f"# Spike report: {','.join(args.countries)}",
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
    ap.add_argument("--countries", default="GB")
    ap.add_argument("--out", default="out/gb")
    ap.add_argument("--minutes", type=float, default=150)
    ap.add_argument("--concurrency", type=int, default=48)
    ap.add_argument("--ckan-max", type=int, default=100_000)
    ap.add_argument("--max-services", type=int, default=0)
    ap.add_argument("--max-services-per-root", type=int, default=1500)
    ap.add_argument("--max-checks", type=int, default=4000)
    ap.add_argument("--host-filter", default="")
    ap.add_argument("--expand-roots", action="store_true", default=True)
    args = ap.parse_args()
    args.countries = [c.strip().upper() for c in args.countries.split(",")]
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
