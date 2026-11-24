"""Build the SQL that loads the agent API's database (Cloudflare D1) from datasets.parquet (+ tags).

Only what search needs goes in the database. Full details stay in the viewer's shard files.
List columns are stored as ',a,b,' so a filter is a simple LIKE '%,a,%'.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import geopandas as gpd
import pandas as pd

# A full reload builds new tables beside the live ones and swaps them in at the end, so search keeps working while
# a 250k-row load runs (it used to drop the tables first). Index names carry a per-load suffix because SQLite index
# names are global and keep their name when the table is renamed.
SCHEMA_TEMPLATE = """DROP TABLE IF EXISTS datasets_next;
CREATE TABLE datasets_next (
  id TEXT PRIMARY KEY, title TEXT, publisher TEXT, ptype TEXT, role TEXT, country TEXT,
  xmin REAL, ymin REAL, xmax REAL, ymax REAL, area REAL,
  pass INTEGER, score INTEGER, themes TEXT, themes_src TEXT, concepts TEXT, protocols TEXT, caps TEXT,
  detail TEXT, detail_m REAL, coverage TEXT, cors INTEGER, xsus INTEGER, open_licence INTEGER, licence TEXT,
  gtypes TEXT, home TEXT
) WITHOUT ROWID;
CREATE INDEX ix_x_{s} ON datasets_next (xmin, xmax);
CREATE INDEX ix_y_{s} ON datasets_next (ymin, ymax);
CREATE INDEX ix_rank_{s} ON datasets_next (pass, score, xmin, xmax, ymin, ymax, home);
DROP TABLE IF EXISTS ds_fts_next;
CREATE VIRTUAL TABLE ds_fts_next USING fts5(id UNINDEXED, title, publisher, body, tokenize='unicode61 remove_diacritics 2');
DROP TABLE IF EXISTS ds_cell_next;
CREATE TABLE ds_cell_next (key TEXT, id TEXT, x0 REAL, y0 REAL, x1 REAL, y1 REAL, PRIMARY KEY (key, id)) WITHOUT ROWID;
CREATE INDEX ix_cell_id_{s} ON ds_cell_next (id);
CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT);
"""
SWAP = ("DROP TABLE IF EXISTS datasets;\nALTER TABLE datasets_next RENAME TO datasets;\n"
        "DROP TABLE IF EXISTS ds_fts;\nALTER TABLE ds_fts_next RENAME TO ds_fts;\n"
        "DROP TABLE IF EXISTS ds_cell;\nALTER TABLE ds_cell_next RENAME TO ds_cell;\n")
SCHEMA = SCHEMA_TEMPLATE  # what the layout hash is taken from


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


# Incremental loads write into the live tables, which a full load has always created first.
CREATE_IF_MISSING = "CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT);\n"


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


def build_rows(ds, tags, gtypes=None, home=None, fts=None, cells=None) -> dict:
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
            bool(r.get("open_licence")), _txt(r.get("licence"))[:200],
            wrap(gtypes.get(r["dataset_id"], [])), home(r) if home else "",
        ]
        if fts is not None:
            fts[r["dataset_id"]] = fts_row(r, tg)
        if cells is not None:
            row = rows[r["dataset_id"]]
            cells[r["dataset_id"]] = cell_keys(x0, y0, x1, y1, row[-1], [c for c in row[15].split(",") if c])
    return rows


# Full-text search (17-18 Nov): `text` searches used LIKE '%x%', which reads every row; for world-wide areas that is
# the whole table, twice (sort and count), and D1 refused ("overloaded"). ds_fts indexes title, publisher and a body
# of tags and the start of the description. Its rowid is derived from the dataset id, so an incremental load can
# delete a dataset's entry directly.
FTS_BODY_CHARS = 300


def fts_rowid(dataset_id: str) -> int:
    import hashlib

    return int(hashlib.sha1(str(dataset_id).encode()).hexdigest()[:15], 16)


def _txt(v) -> str:
    """A text field as a string: None, NaN (a float after a merge) and other non-strings become ""."""
    return v if isinstance(v, str) else ""


def fts_row(r: dict, tg) -> list:
    concepts = list(tg["concepts"]) if tg is not None else []
    themes = list(tg["iso_themes"]) if tg is not None else list(r.get("iso_themes_declared") if r.get("iso_themes_declared") is not None else [])
    kw = r.get("keywords")
    kw = list(kw)[:20] if kw is not None and not isinstance(kw, str) else []
    words = [c.replace("-", " ") for c in concepts + themes] + [str(k) for k in kw]
    body = " ".join(words) + " " + _txt(r.get("abstract"))[:FTS_BODY_CHARS]
    return [fts_rowid(r["dataset_id"]), r["dataset_id"], _txt(r["title"]), _txt(r["publisher"]), body.strip()]


# Spatial index (18 Nov). Area searches filtered on xmin/xmax/ymin/ymax, and a range on one column can't narrow the
# other three, so a 5 km search read ~270k rows; a concept over a large area read the whole rank index. Each dataset
# now gets quadtree cell keys: its level is the finest at which its extent spans at most 2 x 2 cells (lon/lat cells,
# 360/2^L by 180/2^L degrees, levels 0-18), and it has one key per cell (up to 4). A key starts with the dataset's
# home country, so search reads only the countries it would keep anyway:
#   "<home>:<quadkey>"             e.g. "GB:031203..."; home is "" for international or unplaced datasets
#   "c:<concept>|<home>:<quadkey>"  the same per concept, so a concept search reads only that concept
# Each key row also carries the dataset's extent, rounded outwards to 0.001 degrees, so search can drop datasets whose
# cell meets the area but whose extent doesn't before looking them up (about 40% of a city search's keys).
# The rank index also holds extent and home, so a large-area search can sample the best-scored datasets without lookups.
# datasets is a WITHOUT ROWID table, so looking a dataset up by id is one read rather than an index read plus a row.
# The Worker (worker/src/index.js, cellSelect) reads exact keys for the levels coarser than the search area and key
# ranges (prefixes) for the area's own level and finer. Keep the two in step.
MAX_LEVEL = 18
CELLS_VERSION = "cells-1"  # change when cell keys are made differently: forces a full reload


def cell_level(x0, y0, x1, y1) -> int:
    import math

    for lv in range(MAX_LEVEL, -1, -1):
        w, h = 360 / 2 ** lv, 180 / 2 ** lv
        if math.floor((x1 + 180) / w) - math.floor((x0 + 180) / w) <= 1 and math.floor((y1 + 90) / h) - math.floor((y0 + 90) / h) <= 1:
            return lv
    return 0


def quadkey(ix: int, iy: int, lv: int) -> str:
    # digit = 2 * (y bit) + (x bit), most significant level first
    return "".join(str(((iy >> b) & 1) * 2 + ((ix >> b) & 1)) for b in range(lv - 1, -1, -1))


def cell_keys(x0, y0, x1, y1, home: str, concepts) -> list[str]:
    import math

    x0, x1 = max(-180.0, min(180.0, x0)), max(-180.0, min(180.0, x1))
    y0, y1 = max(-90.0, min(90.0, y0)), max(-90.0, min(90.0, y1))
    lv = cell_level(x0, y0, x1, y1)
    w, h, top = 360 / 2 ** lv, 180 / 2 ** lv, 2 ** lv - 1
    qks = [quadkey(ix, iy, lv)
           for ix in range(min(math.floor((x0 + 180) / w), top), min(math.floor((x1 + 180) / w), top) + 1)
           for iy in range(min(math.floor((y0 + 90) / h), top), min(math.floor((y1 + 90) / h), top) + 1)]
    plain = [f"{home}:{k}" for k in qks]
    return list(dict.fromkeys(plain + [f"c:{c}|{p}" for c in concepts for p in plain]))  # a concept can be tagged twice


def inserts(values, verb: str = "INSERT", table: str = "datasets", cols: str = "", rows: int = 40):
    batch, size = [], 0
    for v in values:
        batch.append(v); size += len(v)
        if len(batch) == rows or size > 60_000:  # D1 caps a statement at 100 KB
            yield f"{verb} INTO {table}{cols} VALUES " + ",".join(batch) + ";"
            batch, size = [], 0
    if batch:
        yield f"{verb} INTO {table}{cols} VALUES " + ",".join(batch) + ";"


def main():
    import hashlib
    import itertools
    import json
    import math

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
    fts, cells = {}, {}
    rows = build_rows(ds, tags, gt, home_of(), fts, cells)
    print(f"cell keys: {sum(map(len, cells.values()))} for {len(cells)} datasets")
    print(f"geometry types known for {sum(1 for v in rows.values() if v[-2])} datasets; home country set for {sum(1 for v in rows.values() if v[-1])}")
    sql_vals = {k: "(" + ",".join(q(v) for v in vals) + ")" for k, vals in rows.items()}
    fts_vals = {k: "(" + ",".join(q(v) for v in vals) + ")" for k, vals in fts.items()}
    def box(k):
        r = rows[k]
        return ",".join(repr(round(f(v * 1000) / 1000, 3)) for f, v in ((math.floor, r[6]), (math.floor, r[7]), (math.ceil, r[8]), (math.ceil, r[9])))

    def cell_vals(ids):  # made as written: 1.9M key rows held as strings ran a 7 GB machine out of memory
        for k in ids:
            b = box(k)
            for c in cells.get(k, []):
                yield f"({q(c)},{q(k)},{b})"
    # Cell keys follow from the row's extent, home and concepts, so the row hash covers them; a change to how keys are
    # made changes CELLS_VERSION, which forces a full reload like a table layout change.
    hashes = {k: hashlib.sha1((v + fts_vals.get(k, "")).encode()).hexdigest()[:12] for k, v in sql_vals.items()}
    FTS_COLS = "(rowid, id, title, publisher, body)"

    # D1's free tier allows 100k row writes a day (index updates count too), so a full reload of 40k rows
    # is expensive. With the previous load's hashes we write only what changed.
    prev = json.loads(Path(args.previous).read_text()) if args.previous and Path(args.previous).exists() else None
    # A changed table layout (new columns, 17 Nov: gtypes, home) can't be loaded row by row: reload in full.
    hashes["__schema__"] = hashlib.sha1((SCHEMA + CELLS_VERSION).encode()).hexdigest()[:12]
    if prev is not None and prev.get("__schema__") != hashes["__schema__"]:
        print("table layout changed: full reload")
        prev = None
    if prev is None:
        suffix = hashlib.sha1(f"{args.built}{len(rows)}".encode()).hexdigest()[:6]
        lines = itertools.chain([SCHEMA_TEMPLATE.replace("{s}", suffix)], inserts(sql_vals.values(), table="datasets_next"),
                                inserts(fts_vals.values(), table="ds_fts_next", cols=FTS_COLS),
                                inserts(cell_vals(rows), "INSERT OR IGNORE", table="ds_cell_next", rows=500), [SWAP])
        mode, changed, removed = "full", len(rows), 0
    else:
        changed_ids = [k for k, h in hashes.items() if prev.get(k) != h and k != "__schema__"]
        removed_ids = [k for k in prev if k not in hashes and k != "__schema__"]
        head = [CREATE_IF_MISSING] if (changed_ids or removed_ids) else []
        for i in range(0, len(removed_ids), 200):
            head.append("DELETE FROM datasets WHERE id IN (" + ",".join(q(x) for x in removed_ids[i:i + 200]) + ");")
        gone = removed_ids + changed_ids
        for i in range(0, len(gone), 200):
            head.append("DELETE FROM ds_fts WHERE rowid IN (" + ",".join(str(fts_rowid(x)) for x in gone[i:i + 200]) + ");")
            head.append("DELETE FROM ds_cell WHERE id IN (" + ",".join(q(x) for x in gone[i:i + 200]) + ");")
        lines = itertools.chain(head, inserts((sql_vals[k] for k in changed_ids), "INSERT OR REPLACE"),
                                inserts((fts_vals[k] for k in changed_ids if k in fts_vals), table="ds_fts", cols=FTS_COLS),
                                inserts(cell_vals(changed_ids), "INSERT OR IGNORE", table="ds_cell", rows=500))
        mode, changed, removed = "incremental", len(changed_ids), len(removed_ids)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    wrote = 0
    with open(args.out, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n"); wrote += 1
        if wrote:
            f.write(f"INSERT OR REPLACE INTO meta VALUES ('built', {q(args.built)}), ('count', {q(str(len(rows)))}), ('tagged', {q(str(len(tags)))});\n")
    if args.hashes_out:
        Path(args.hashes_out).write_text(json.dumps(hashes, separators=(",", ":")))
    print(f"{mode}: {len(rows)} datasets, {changed} to write, {removed} to delete, {len(tags)} tags; "
          f"{Path(args.out).stat().st_size / 1e6:.2f} MB of SQL")


if __name__ == "__main__":
    main()
