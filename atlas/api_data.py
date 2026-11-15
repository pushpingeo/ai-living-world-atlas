"""Build the SQL that loads the agent API's database (Cloudflare D1) from datasets.parquet (+ tags).

Only what search needs goes in the database. Full details stay in the viewer's shard files.
List columns are stored as ',a,b,' so a filter is a simple LIKE '%,a,%'.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import geopandas as gpd
import pandas as pd

SCHEMA = """DROP TABLE IF EXISTS datasets;
CREATE TABLE datasets (
  id TEXT PRIMARY KEY, title TEXT, publisher TEXT, ptype TEXT, role TEXT, country TEXT,
  xmin REAL, ymin REAL, xmax REAL, ymax REAL, area REAL,
  pass INTEGER, score INTEGER, themes TEXT, themes_src TEXT, concepts TEXT, protocols TEXT, caps TEXT,
  detail TEXT, detail_m REAL, coverage TEXT, cors INTEGER, xsus INTEGER, open_licence INTEGER, licence TEXT
);
CREATE INDEX ix_x ON datasets (xmin, xmax);
CREATE INDEX ix_y ON datasets (ymin, ymax);
DROP TABLE IF EXISTS meta;
CREATE TABLE meta (k TEXT PRIMARY KEY, v TEXT);
"""


def q(v) -> str:
    if v is None or (isinstance(v, float) and v != v):
        return "NULL"
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, (int, float)):
        return repr(round(v, 6)) if isinstance(v, float) else str(v)
    return "'" + str(v).replace("'", "''") + "'"


def wrap(vals) -> str:
    vals = [] if vals is None else [str(x) for x in vals]
    return "," + ",".join(vals) + "," if vals else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datasets", required=True)
    ap.add_argument("--tags", default="")
    ap.add_argument("--out", default="out/api.sql")
    ap.add_argument("--built", default="")
    args = ap.parse_args()

    ds = gpd.read_parquet(args.datasets)
    tags = {}
    if args.tags and Path(args.tags).exists():
        t = pd.read_parquet(args.tags)
        tags = {r["dataset_id"]: r for r in t[t["status"] == "succeeded"].to_dict("records")}

    lines = [SCHEMA]
    batch = []
    n = 0
    for r, g in zip(ds.drop(columns="geometry").to_dict("records"), ds.geometry):
        if g is None or g.is_empty:
            continue
        x0, y0, x1, y1 = g.bounds
        tg = tags.get(r["dataset_id"])
        themes = list(tg["iso_themes"]) if tg is not None else list(r["iso_themes_declared"])
        flags = list(r.get("extent_flags") if r.get("extent_flags") is not None else [])
        vals = [
            r["dataset_id"], r["title"], r["publisher"], r["publisher_type"], r["role"], r.get("country") or "",
            x0, y0, x1, y1, (x1 - x0) * (y1 - y0),
            bool(r["q_pass"]), int(r["q_total"]), wrap(themes), "ai" if tg is not None else ("declared" if themes else ""),
            wrap(tg["concepts"] if tg is not None else []), wrap(r["protocols"]), wrap(r["capabilities"]),
            r.get("detail_level") or "", r.get("detail_m"), r.get("coverage_level") or "",
            any(e.get("cors") for e in __import__("json").loads(r["endpoints"] or "[]")),
            bool(flags) and r.get("extent_source", "declared") != "measured",
            bool(r.get("open_licence")), (r.get("licence") or "")[:200],
        ]
        batch.append("(" + ",".join(q(v) for v in vals) + ")")
        n += 1
        if len(batch) == 40 or sum(map(len, batch)) > 60_000:  # D1 caps a statement at 100 KB
            lines.append("INSERT INTO datasets VALUES " + ",".join(batch) + ";")
            batch = []
    if batch:
        lines.append("INSERT INTO datasets VALUES " + ",".join(batch) + ";")
    lines.append(f"INSERT INTO meta VALUES ('built', {q(args.built)}), ('count', {q(str(n))}), ('tagged', {q(str(len(tags)))});")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text("\n".join(lines) + "\n")
    print(f"{args.out}: {n} datasets, {len(tags)} tagged, {Path(args.out).stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
