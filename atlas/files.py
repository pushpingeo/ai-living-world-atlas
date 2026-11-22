"""Download-only datasets the atlas hosts itself (e.g. Global Energy Monitor's trackers, which come as files by
request form). Each has a spec in vocab/files/<id>.yaml. This script turns the publisher's file into map tiles in
files/<id>/ (gzipped GeoJSON per grid cell, plus index.json), which the pages build publishes at data/f/<id>/, and
writes the catalogue record into vocab/seeds/files.yaml, which the `spike-files` wave turns into a dataset that
fetch_features can query (the Worker reads only the tiles near the area asked for).

Usage: python -m atlas.files --source-dir DIR vocab/files/gem-goget.yaml [more specs...]
Only publishers whose licence allows redistribution (e.g. CC BY 4.0) belong here: we host a copy.

Spec keys: id, title, publisher, publisher_type, licence, citation, release, landing_page, abstract, concepts_hint,
  source        file name in --source-dir; "archive.zip!member" for a file inside a zip
  sheets        list of sheet names (spreadsheets); rows from all are combined, with a "sheet" property if several
  wkt_column    outline/route column in WKT (used when valid lon/lat near the row's point)
  coords_column one "lat, lon" text column, when there are no separate latitude/longitude columns
  exclude       {column: regex}: rows to leave out (e.g. third-party rows under a non-commercial licence)
  simplify_deg  geometry simplification tolerance, default 0.0005 (~50 m)
  source_url    where the `files` workflow downloads the source from (publishers whose download is open, e.g. JNCC)
  country, endpoint_info, attribution   passed to the record: home country, details for get_dataset (e.g. name_field),
                and the publisher's attribution statement (also give it in vocab/licence_overrides.yaml)
"""
from __future__ import annotations

import argparse
import gzip
import io
import json
import math
import re
import shutil
import zipfile
from collections import defaultdict
from datetime import date
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent
PAGES_BASE = "https://pushpingeo.github.io/ai-living-world-atlas/data/f/"
LAT = re.compile(r"^(lat|latitude)$", re.I)
LON = re.compile(r"^(lon|long|longitude|lng)$", re.I)
TILE_DEG = 10  # grid cell size for tiles; a feature goes in the cell of its first coordinate


def clean(v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    if isinstance(v, (pd.Timestamp, date)):
        return v.isoformat()[:10]
    if hasattr(v, "item"):
        v = v.item()
    if isinstance(v, float) and v.is_integer() and abs(v) < 1e15:
        return int(v)
    return v


def _round(g):
    def r(c):
        return [round(c[0], 5), round(c[1], 5)] if isinstance(c[0], (int, float)) else [r(x) for x in c]
    if g["type"] == "GeometryCollection":
        return g
    return {"type": g["type"], "coordinates": r(g["coordinates"])}


def _first(c):
    while not isinstance(c[0], (int, float)):
        c = c[0]
    return c


def _bounds(c, bb):
    if isinstance(c[0], (int, float)):
        bb[0], bb[1], bb[2], bb[3] = min(bb[0], c[0]), min(bb[1], c[1]), max(bb[2], c[0]), max(bb[3], c[1])
    else:
        for x in c:
            _bounds(x, bb)
    return bb


def open_source(src_dir: Path, source: str):
    """A path or a file-like object for 'name' or 'archive.zip!member'. A shapefile inside a zip is read in place
    (zip://), because it needs its .dbf, .shx and .prj beside it."""
    if "!" in source:
        zname, member = source.split("!", 1)
        if re.search(r"\.shp$", member, re.I):
            return f"zip://{(src_dir / zname).resolve()}!{member}", member
        return io.BytesIO(zipfile.ZipFile(src_dir / zname).read(member)), member
    return src_dir / source, source


def rows_to_features(df: pd.DataFrame, spec: dict, stats: dict) -> list:
    from shapely import wkt as _wkt
    from shapely.geometry import mapping

    cols = [str(c).strip() for c in df.columns]
    df.columns = cols
    lat = next((c for c in cols if LAT.match(c)), None)
    lon = next((c for c in cols if LON.match(c)), None)
    cc = spec.get("coords_column")
    wcol = spec.get("wkt_column") or ""
    tol = float(spec.get("simplify_deg", 0.0005))
    for col, rx in (spec.get("exclude") or {}).items():
        if col in df.columns:
            m = df[col].astype(str).str.contains(rx, regex=True, na=False)
            stats["excluded"] += int(m.sum())
            df = df[~m]
    skip = {c for c in (lat, lon, wcol, cc) if c}
    keep = spec.get("columns") or [c for c in cols if c not in skip and not c.lower().startswith("unnamed")]
    out = []
    for _, r in df.iterrows():
        py = px = None
        try:
            if lat and lon:
                py, px = float(r[lat]), float(r[lon])
            elif cc and isinstance(r.get(cc), str):
                a, b = [float(x) for x in r[cc].replace(";", ",").split(",")[:2]]
                py, px = a, b
        except (TypeError, ValueError):
            pass
        if py is not None and (math.isnan(px) or math.isnan(py) or abs(py) > 90 or abs(px) > 180):
            py = px = None
        geom = None
        w = r.get(wcol) if wcol else None
        if isinstance(w, str) and w.strip():
            try:
                g = _wkt.loads(w)
                b = g.bounds if not g.is_empty else None
                ok = b and -180 <= b[0] <= b[2] <= 180 and -90 <= b[1] <= b[3] <= 90
                if ok and px is not None:  # near the row's own point (catches swapped axes)
                    ok = b[0] - 2 <= px <= b[2] + 2 and b[1] - 2 <= py <= b[3] + 2
                if ok:
                    geom = mapping(g.simplify(tol, preserve_topology=True))
                    stats["outlines"] += 1
                elif b:
                    stats["bad_outlines"] += 1
            except Exception:
                stats["bad_outlines"] += 1
        if geom is None:
            if px is None:
                stats["no_location"] += 1
                continue
            geom = {"type": "Point", "coordinates": [px, py]}
        props = {k: clean(r.get(k)) for k in keep if k in df.columns}
        props = {k: v for k, v in props.items() if v not in (None, "")}
        props["geometry_source"] = "point" if geom["type"] == "Point" else "outline"
        out.append({"type": "Feature", "geometry": _round(geom), "properties": props})
    return out


def vector_to_features(f, spec: dict, stats: dict) -> list:
    import geopandas as gpd
    from shapely.geometry import mapping

    g = gpd.read_file(f)
    if g.crs and g.crs.to_epsg() != 4326:
        g = g.to_crs(4326)
    tol = float(spec.get("simplify_deg", 0.0005))
    for col, rx in (spec.get("exclude") or {}).items():
        if col in g.columns:
            m = g[col].astype(str).str.contains(rx, regex=True, na=False)
            stats["excluded"] += int(m.sum())
            g = g[~m]
    keep = spec.get("columns") or [c for c in g.columns if c != "geometry"]
    out = []
    for geom, (_, r) in zip(g.geometry, g.iterrows()):
        if geom is None or geom.is_empty:
            stats["no_location"] += 1
            continue
        props = {k: clean(r.get(k)) for k in keep}
        props = {k: v for k, v in props.items() if v not in (None, "")}
        out.append({"type": "Feature", "geometry": _round(mapping(geom.simplify(tol, preserve_topology=True))), "properties": props})
        stats["outlines"] += geom.geom_type != "Point"
    return out


def convert(spec: dict, src_dir: Path) -> tuple[list, dict, str]:
    stats = defaultdict(int)
    f, name = open_source(src_dir, spec["source"])
    about = ""
    if re.search(r"\.(xlsx|xls)$", name, re.I):
        xl = pd.ExcelFile(f)
        sheets = spec.get("sheets") or [spec["sheet"]]
        feats = []
        for s in sheets:
            df = xl.parse(s)
            stats["rows"] += len(df)
            fs = rows_to_features(df, spec, stats)
            if len(sheets) > 1:
                for x in fs:
                    x["properties"]["sheet"] = s
            feats += fs
        for s in xl.sheet_names:
            if re.search(r"about|read ?me|licen", s, re.I):
                about = " ".join(str(x) for x in xl.parse(s, header=None).fillna("").values.ravel() if str(x).strip())[:4000]
                break
    else:
        feats = vector_to_features(f, spec, stats)
        stats["rows"] = len(feats) + stats["no_location"] + stats["excluded"]
    return feats, dict(stats), about


def write_tiles(spec: dict, feats: list, stats: dict) -> dict:
    out = ROOT / "files" / spec["id"]
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    cells = defaultdict(list)
    for x in feats:
        lon, lat = _first(x["geometry"]["coordinates"])
        cells[(int(math.floor(lon / TILE_DEG)), int(math.floor(lat / TILE_DEG)))].append(x)
    tiles, total = [], 0
    for (cx, cy), fs in sorted(cells.items()):
        bb = [math.inf, math.inf, -math.inf, -math.inf]
        for x in fs:
            _bounds(x["geometry"]["coordinates"], bb)
        key = f"{cx}_{cy}"
        data = gzip.compress(json.dumps({"type": "FeatureCollection", "features": fs}, separators=(",", ":"),
                                        ensure_ascii=False).encode(), compresslevel=9, mtime=0)
        (out / f"{key}.json.gz").write_bytes(data)
        total += len(data)
        tiles.append({"key": key, "bbox": [round(v, 5) for v in bb], "n": len(fs)})
    bb = [min(t["bbox"][0] for t in tiles), min(t["bbox"][1] for t in tiles),
          max(t["bbox"][2] for t in tiles), max(t["bbox"][3] for t in tiles)] if tiles else None
    index = {
        "atlas_source": {"publisher": spec["publisher"], "citation": spec.get("citation", ""), "licence": spec["licence"],
                         "release": spec.get("release", ""), "landing_page": spec.get("landing_page", ""),
                         "converted": date.today().isoformat(), "source_file": spec["source"].split("!")[-1],
                         **{k: v for k, v in stats.items()}},
        "count": len(feats), "bbox": bb, "tile_deg": TILE_DEG, "format": "gzip GeoJSON per tile", "tiles": tiles,
    }
    (out / "index.json").write_text(json.dumps(index, separators=(",", ":")))
    print(f"files/{spec['id']}/: {len(feats):,} features in {len(tiles)} tiles, {total / 1e6:.1f} MB gzipped; {stats}")
    return index


def record(spec: dict, index: dict, feats: list) -> dict:
    types = {x["geometry"]["type"] for x in feats}
    gtype = "line" if types & {"LineString", "MultiLineString"} else "polygon" if types & {"Polygon", "MultiPolygon"} else "point"
    left = []
    if index["atlas_source"].get("no_location"):
        left.append(f"{index['atlas_source']['no_location']:,} records without a location")
    if index["atlas_source"].get("excluded"):
        left.append(f"{index['atlas_source']['excluded']:,} records excluded ({spec.get('exclude_reason', 'see spec')})")
    return {
        "kind": "record", "id": spec["id"], "title": spec["title"], "publisher": spec["publisher"],
        "publisher_type": spec.get("publisher_type", "civil-society"), **({"country": spec["country"]} if spec.get("country") else {}),
        "abstract": spec["abstract"].strip() + (f" Release: {spec['release']}." if spec.get("release") else "")
                    + f" {index['count']:,} features" + (f"; left out: {'; '.join(left)}" if left else "") + "."
                    + f" Hosted by the atlas as a copy of the publisher's download; cite as: {spec.get('citation', spec['publisher'])}.",
        "licence": spec["licence"], "landing_page": spec.get("landing_page", ""),
        "bbox": [round(x, 4) for x in index["bbox"]], "geometry_type": gtype,
        "concepts_hint": spec.get("concepts_hint", []),
        "endpoints": [{"protocol": "geojson", "url": PAGES_BASE + f"{spec['id']}/index.json", "format": "GeoJSON tiles",
                       **({"info": spec["endpoint_info"]} if spec.get("endpoint_info") else {})},
                      {"protocol": "landing", "url": spec.get("landing_page", "")}],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("specs", nargs="+")
    ap.add_argument("--source-dir", required=True)
    args = ap.parse_args()
    seeds = ROOT / "vocab" / "seeds" / "files.yaml"
    doc = yaml.safe_load(seeds.read_text()) if seeds.exists() else {"defaults": {"publisher_type": "civil-society"}, "sources": []}
    for p in args.specs:
        spec = yaml.safe_load(Path(p).read_text())
        feats, stats, about = convert(spec, Path(args.source_dir))
        if not feats:
            print(f"{spec['id']}: no features, skipped")
            continue
        index = write_tiles(spec, feats, stats)
        old = ROOT / "files" / f"{spec['id']}.geojson"  # single-file layout before tiles (18 Nov)
        if old.exists():
            old.unlink()
        doc["sources"] = [s for s in doc["sources"] if s.get("id") != spec["id"]] + [record(spec, index, feats)]
    doc["sources"].sort(key=lambda s: s["id"])
    seeds.write_text("# Written by atlas/files.py from vocab/files/*.yaml: datasets the atlas hosts as files.\n"
                     + yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=120))
    print(f"{len(doc['sources'])} catalogue records in {seeds.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
