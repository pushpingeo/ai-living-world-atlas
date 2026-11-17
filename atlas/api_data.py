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
  detail TEXT, detail_m REAL, coverage TEXT, cors INTEGER, xsus INTEGER, open_licence INTEGER, licence TEXT,
  gtypes TEXT, home TEXT
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
    # One statement per line: the deploy cuts the file into pieces at lines ending in ";", so a newline inside a
    # value could leave a piece starting mid-string (17 Nov, "near Parametrix"). Search needs no line breaks.
    return "'" + " ".join(str(v).split("\n")).replace("\r", " ").replace("'", "''") + "'"


def wrap(vals) -> str:
    vals = [] if vals is None else [str(x) for x in vals]
    return "," + ",".join(vals) + "," if vals else ""


TABLE = SCHEMA.split("CREATE TABLE datasets", 1)[1].split(";", 1)[0]
CREATE_IF_MISSING = (
    "CREATE TABLE IF NOT EXISTS datasets" + TABLE + ";\n"
    "CREATE INDEX IF NOT EXISTS ix_x ON datasets (xmin, xmax);\n"
    "CREATE INDEX IF NOT EXISTS ix_y ON datasets (ymin, ymax);\n"
    "CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT);\n"
)


# Layer geometry types from the crawl → what a search needs: point, line or polygon. WFS layers say only
# "features" (the crawl doesn't read DescribeFeatureType), so their type stays unknown.
GTYPE = {"point": "point", "multipoint": "point", "polyline": "line", "polygon": "polygon"}


def dataset_gtypes(layers) -> dict:
    """dataset_id -> sorted list of point/line/polygon across its layers."""
    if layers is None or "geometry_type" not in layers.columns:
        return {}
    ly = layers[["dataset_id", "geometry_type"]].dropna()
    ly = ly.assign(g=ly["geometry_type"].map(GTYPE)).dropna(subset=["g"])
    return {k: sorted(set(v)) for k, v in ly.groupby("dataset_id")["g"]}


# Which country a dataset is about, for search: a national publisher's layer is about its own country, whatever
# extent it declares (Kentucky wells, US census blocks and NOAA's US demarcation lines all claimed the world and came
# up for Nigeria, 17 Nov). The MCP server leaves out datasets whose home country doesn't touch the search area.
# Blank for publishers with no country, international bodies, and datasets listed as genuinely wider.
EXTENT_OVERRIDES = Path(__file__).resolve().parent.parent / "vocab" / "extent_overrides.yaml"


def home_of():
    import re

    import yaml

    keep = [re.compile(p, re.I) for p in (yaml.safe_load(EXTENT_OVERRIDES.read_text()) or {}).get("genuinely_wider", [])] if EXTENT_OVERRIDES.exists() else []

    def home(r):
        c = (r.get("country") or "").strip().upper()
        if c == "EUROPE":
            return "EU"
        if not re.fullmatch(r"[A-Z]{2}", c) or re.search(r"international|intergov", r.get("publisher_type") or "", re.I):
            return ""
        return "" if any(k.search(f"{r['title']} | {r['publisher']}") for k in keep) else c
    return home


def build_rows(ds, tags, gtypes=None, home=None) -> dict:
    import json

    gtypes = gtypes or {}
    rows = {}
    for r, g in zip(ds.drop(columns="geometry").to_dict("records"), ds.geometry):
        if g is None or g.is_empty:
            continue
        x0, y0, x1, y1 = g.bounds
        tg = tags.get(r["dataset_id"])
        themes = list(tg["iso_themes"]) if tg is not None else list(r["iso_themes_declared"])
        flags = list(r.get("extent_flags") if r.get("extent_flags") is not None else [])
        rows[r["dataset_id"]] = [
            r["dataset_id"], r["title"], r["publisher"], r["publisher_type"], r["role"], r.get("country") or "",
            x0, y0, x1, y1, (x1 - x0) * (y1 - y0),
            bool(r["q_pass"]), int(r["q_total"]), wrap(themes), "ai" if tg is not None else ("declared" if themes else ""),
            wrap(tg["concepts"] if tg is not None else []), wrap(r["protocols"]), wrap(r["capabilities"]),
            r.get("detail_level") or "", r.get("detail_m"), r.get("coverage_level") or "",
            any(e.get("cors") for e in json.loads(r["endpoints"] or "[]")),
            bool(flags) and r.get("extent_source", "declared") != "measured",
            bool(r.get("open_licence")), (r.get("licence") or "")[:200],
            wrap(gtypes.get(r["dataset_id"], [])), home(r) if home else "",
        ]
    return rows


def inserts(values: list[str], verb: str = "INSERT") -> list[str]:
    out, batch = [], []
    for v in values:
        batch.append(v)
        if len(batch) == 40 or sum(map(len, batch)) > 60_000:  # D1 caps a statement at 100 KB
            out.append(f"{verb} INTO datasets VALUES " + ",".join(batch) + ";")
            batch = []
    if batch:
        out.append(f"{verb} INTO datasets VALUES " + ",".join(batch) + ";")
    return out


def main():
    import hashlib
    import json

    ap = argparse.ArgumentParser()
    ap.add_argument("--datasets", required=True)
    ap.add_argument("--tags", default="")
    ap.add_argument("--layers", default="", help="layers.parquet, for each dataset's geometry types")
    ap.add_argument("--only-passing", action="store_true", help="carry only datasets that pass the quality bar")
    ap.add_argument("--out", default="out/api.sql")
    ap.add_argument("--built", default="")
    ap.add_argument("--previous", default="", help="rows.json from the last load: only changed rows are written")
    ap.add_argument("--hashes-out", default="", help="where to write rows.json for next time")
    args = ap.parse_args()

    ds = gpd.read_parquet(args.datasets)
    if args.only_passing:
        ds = ds[ds["q_pass"].astype(bool)].reset_index(drop=True)
    tags = {}
    if args.tags and Path(args.tags).exists():
        t = pd.read_parquet(args.tags)
        tags = {r["dataset_id"]: r for r in t[t["status"] == "succeeded"].to_dict("records")}
    layers = pd.read_parquet(args.layers, columns=["dataset_id", "geometry_type"]) if args.layers and Path(args.layers).exists() and "geometry_type" in __import__("pyarrow.parquet", fromlist=["x"]).read_schema(args.layers).names else None
    gt = dataset_gtypes(layers)
    rows = build_rows(ds, tags, gt, home_of())
    print(f"geometry types known for {sum(1 for v in rows.values() if v[-2])} datasets; home country set for {sum(1 for v in rows.values() if v[-1])}")
    sql_vals = {k: "(" + ",".join(q(v) for v in vals) + ")" for k, vals in rows.items()}
    hashes = {k: hashlib.sha1(v.encode()).hexdigest()[:12] for k, v in sql_vals.items()}

    # D1's free tier allows 100k row writes a day (index updates count too), so a full reload of 40k rows
    # is expensive. With the previous load's hashes we write only what changed.
    prev = json.loads(Path(args.previous).read_text()) if args.previous and Path(args.previous).exists() else None
    # A changed table layout (new columns, 17 Nov: gtypes, home) can't be loaded row by row: reload in full.
    hashes["__schema__"] = hashlib.sha1(SCHEMA.encode()).hexdigest()[:12]
    if prev is not None and prev.get("__schema__") != hashes["__schema__"]:
        print("table layout changed: full reload")
        prev = None
    if prev is None:
        lines = [SCHEMA] + inserts(list(sql_vals.values()))
        mode, changed, removed = "full", len(rows), 0
    else:
        changed_ids = [k for k, h in hashes.items() if prev.get(k) != h and k != "__schema__"]
        removed_ids = [k for k in prev if k not in hashes and k != "__schema__"]
        lines = [CREATE_IF_MISSING] if (changed_ids or removed_ids) else []
        for i in range(0, len(removed_ids), 200):
            lines.append("DELETE FROM datasets WHERE id IN (" + ",".join(q(x) for x in removed_ids[i:i + 200]) + ");")
        lines += inserts([sql_vals[k] for k in changed_ids], "INSERT OR REPLACE")
        mode, changed, removed = "incremental", len(changed_ids), len(removed_ids)
    if lines:
        lines.append(f"INSERT OR REPLACE INTO meta VALUES ('built', {q(args.built)}), ('count', {q(str(len(rows)))}), ('tagged', {q(str(len(tags)))});")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text("\n".join(lines) + ("\n" if lines else ""))
    if args.hashes_out:
        Path(args.hashes_out).write_text(json.dumps(hashes, separators=(",", ":")))
    print(f"{mode}: {len(rows)} datasets, {changed} to write, {removed} to delete, {len(tags)} tags; "
          f"{Path(args.out).stat().st_size / 1e6:.2f} MB of SQL")


if __name__ == "__main__":
    main()
