"""Build the viewer's data files from datasets.parquet (+ tags.parquet if present).

site/data/index.json      one compact row per dataset: what the map and filters need
site/data/d/<xx>.json     details (description, licence, endpoints) sharded by the first 2 hex chars of the id
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import pandas as pd


LEVELS = [(5, "a"), (20, "b")]   # (cell size in degrees, level name), finest first
MAX_CELLS = 4                     # a dataset is copied into at most this many cells of a level


def nn(v):
    """JSON has no NaN: turn pandas missing values into null."""
    if isinstance(v, float) and v != v:
        return None
    if isinstance(v, dict):
        return {k: nn(x) for k, x in v.items()}
    if isinstance(v, list):
        return [nn(x) for x in v]
    return v


def lst(v):
    return [] if v is None or (isinstance(v, float) and pd.isna(v)) else list(v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datasets", required=True)
    ap.add_argument("--tags", default="")
    ap.add_argument("--out", default="site/data")
    ap.add_argument("--meta", default="{}", help="JSON merged into meta (run ids, dates)")
    args = ap.parse_args()
    out = Path(args.out)
    (out / "d").mkdir(parents=True, exist_ok=True)

    import geopandas as gpd

    ds = gpd.read_parquet(args.datasets)
    ds["_bbox"] = [list(g.bounds) if g is not None and not g.is_empty else None for g in ds.geometry]
    ds = pd.DataFrame(ds.drop(columns="geometry"))
    tags = {}
    if args.tags and Path(args.tags).exists():
        t = pd.read_parquet(args.tags)
        t = t[t["status"] == "succeeded"]
        tags = {r["dataset_id"]: r for r in t.to_dict("records")}

    protocols, roles, ptypes, themes, concepts, caps, details = {}, {}, {}, {}, {}, {}, {}

    def code(table, v):
        if v not in table:
            table[v] = len(table)
        return table[v]

    rows = []
    shards = defaultdict(dict)
    for r in ds.to_dict("records"):
        bbox = r.get("_bbox")
        if bbox is None:
            continue
        tg = tags.get(r["dataset_id"])
        th = lst(tg["iso_themes"]) if tg is not None else lst(r.get("iso_themes_declared"))
        th_src = "ai" if tg is not None else ("declared" if th else "")
        co = lst(tg["concepts"]) if tg is not None else []
        eps = json.loads(r["endpoints"]) if r.get("endpoints") else []
        cors_any = any(e.get("cors") for e in eps)
        rows.append([
            r["dataset_id"], r["title"], r["publisher"], code(ptypes, r["publisher_type"]), code(roles, r["role"]),
            [round(float(x), 4) for x in bbox],
            1 if r["q_pass"] else 0, int(r["q_total"]),
            [code(themes, x) for x in th], [code(concepts, x) for x in co],
            [code(protocols, x) for x in lst(r["protocols"])], [code(caps, x) for x in lst(r["capabilities"])],
            r.get("detail_level") or "", 1 if cors_any else 0,
            1 if (lst(r.get("extent_flags")) and r.get("extent_source", "declared") != "measured") else 0,
        ])
        shards[r["dataset_id"][:2]][r["dataset_id"]] = {
            "abstract": (r.get("abstract") or "")[:2000], "licence": (r.get("licence") or "")[:400],
            "open_licence": bool(r.get("open_licence")), "landing_page": r.get("landing_page") or "",
            "keywords": lst(r.get("keywords"))[:20], "coverage": r.get("coverage_level") or "",
            "detail_m": r.get("detail_m"), "detail_source": r.get("detail_source") or "",
            "themes_source": th_src, "tag_reason": (tg.get("reason") if tg is not None else "") or "",
            "tag_confidence": (tg.get("confidence") if tg is not None else None),
            "match_rules": lst(r.get("match_rules")),
            "extent_source": r.get("extent_source") or "declared", "extent_flags": lst(r.get("extent_flags")),
            "endpoints": [{k: e.get(k) for k in ("protocol", "url", "service_url", "layer_name", "capabilities", "check", "cors", "info")} for e in eps],
        }

    inv = lambda t: [k for k, _ in sorted(t.items(), key=lambda kv: kv[1])]
    meta = {
        "fields": ["id", "title", "publisher", "ptype", "role", "bbox", "pass", "score", "themes", "concepts",
                   "protocols", "caps", "detail", "cors", "xsus"],
        "ptypes": inv(ptypes), "roles": inv(roles), "themes": inv(themes), "concepts": inv(concepts),
        "protocols": inv(protocols), "caps": inv(caps), "count": len(rows), "tagged": len(tags),
        "levels": [{"deg": d, "name": n} for d, n in LEVELS],
        **json.loads(args.meta),
    }
    # Two levels of spatial tiles. A dataset goes in every cell its extent touches at the finest level where it
    # touches at most MAX_CELLS cells: 5-degree cells for local data, 20-degree cells for regional and national
    # data, and big.json (always loaded) for anything larger.
    big, tiles = [], defaultdict(list)
    for row in rows:
        x0, y0, x1, y1 = row[5]
        for deg, lvl in LEVELS:
            tx0, tx1 = int((x0 + 180) // deg), int((min(x1, 179.999) + 180) // deg)
            ty0, ty1 = int((y0 + 90) // deg), int((min(y1, 89.999) + 90) // deg)
            if (tx1 - tx0 + 1) * (ty1 - ty0 + 1) <= MAX_CELLS:
                for tx in range(tx0, tx1 + 1):
                    for ty in range(ty0, ty1 + 1):
                        tiles[f"{lvl}_{tx}_{ty}"].append(row)
                break
        else:
            big.append(row)
    meta["tiles"] = {k: len(v) for k, v in tiles.items()}
    (out / "t").mkdir(parents=True, exist_ok=True)
    dump = lambda o: json.dumps(nn(o), separators=(",", ":"), default=str, allow_nan=False)
    (out / "meta.json").write_text(dump(meta))
    (out / "big.json").write_text(dump(big))
    for k, v in tiles.items():
        (out / "t" / f"{k}.json").write_text(dump(v))
    for k, v in shards.items():
        (out / "d" / f"{k}.json").write_text(dump(v))
    print(f"{len(rows)} datasets, {len(tags)} tagged; big.json {len(big)} rows "
          f"({(out / 'big.json').stat().st_size / 1e6:.1f} MB), {len(tiles)} tiles (largest {max(map(len, tiles.values()), default=0)} rows), "
          f"{len(shards)} detail shards")


if __name__ == "__main__":
    main()
