"""Download-only datasets the atlas hosts itself (e.g. Global Energy Monitor's trackers, which come as an .xlsx
by request form). Each has a spec in vocab/files/<id>.yaml. This script turns the publisher's file into one
GeoJSON in files/<id>.geojson, which the pages build publishes at data/f/<id>.geojson, and writes the catalogue
record into vocab/seeds/files.yaml, which the `spike-files` wave turns into a dataset that fetch_features can query.

Usage: python -m atlas.files vocab/files/gem-goget.yaml path/to/download.xlsx
Only publishers whose licence allows redistribution (e.g. CC BY 4.0) belong here: we host a copy.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from datetime import date
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent
PAGES_BASE = "https://pushpingeo.github.io/ai-living-world-atlas/data/f/"
LAT = re.compile(r"^(lat|latitude|y)$", re.I)
LON = re.compile(r"^(lon|long|longitude|lng|x)$", re.I)


def find_sheet(xl: pd.ExcelFile, spec: dict) -> tuple[str, pd.DataFrame]:
    """The named sheet, or the first sheet with latitude and longitude columns."""
    names = [spec["sheet"]] if spec.get("sheet") else xl.sheet_names
    for s in names:
        df = xl.parse(s)
        cols = [str(c).strip() for c in df.columns]
        if any(LAT.match(c) for c in cols) and any(LON.match(c) for c in cols):
            df.columns = cols
            return s, df
    raise SystemExit(f"no sheet with latitude/longitude columns among {names}")


def clean(v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    if isinstance(v, (pd.Timestamp, date)):
        return v.isoformat()[:10]
    if hasattr(v, "item"):
        v = v.item()
    return v


def convert(spec: dict, src: Path) -> dict:
    """Rows -> features: the WKT outline column when the spec names one and the row has it (simplified to
    spec['simplify_deg'], default ~50 m), otherwise a point from latitude and longitude."""
    from shapely import wkt as _wkt
    from shapely.geometry import mapping

    xl = pd.ExcelFile(src)
    sheet, df = find_sheet(xl, spec)
    lat = next(c for c in df.columns if LAT.match(c))
    lon = next(c for c in df.columns if LON.match(c))
    wcol = spec.get("wkt_column") or ""
    tol = float(spec.get("simplify_deg", 0.0005))
    keep = spec.get("columns") or [c for c in df.columns if c not in (lat, lon, wcol)]
    feats, n_outline, n_bad, n_none = [], 0, 0, 0
    for _, r in df.iterrows():
        geom = None
        w = r.get(wcol) if wcol else None
        if isinstance(w, str) and w.strip():
            try:
                g = _wkt.loads(w)
                b = g.bounds if not g.is_empty else None
                ok = b and -180 <= b[0] <= b[2] <= 180 and -90 <= b[1] <= b[3] <= 90
                try:  # and near the row's own point, when it has one (catches swapped axes)
                    py, px = float(r[lat]), float(r[lon])
                    if ok and not (math.isnan(px) or math.isnan(py)):
                        ok = b[0] - 2 <= px <= b[2] + 2 and b[1] - 2 <= py <= b[3] + 2
                except (TypeError, ValueError):
                    pass
                if ok:
                    geom = mapping(g.simplify(tol, preserve_topology=True))
                    n_outline += 1
                elif b:
                    n_bad += 1  # projected metres or misplaced: the point is used instead
            except Exception:
                n_bad += 1
        if geom is None:
            try:
                y, x = float(r[lat]), float(r[lon])
            except (TypeError, ValueError):
                n_none += 1
                continue
            if math.isnan(x) or math.isnan(y) or abs(y) > 90 or abs(x) > 180:
                n_none += 1
                continue
            geom = {"type": "Point", "coordinates": [x, y]}
        props = {k: clean(r.get(k)) for k in keep if k in df.columns}
        props["geometry_source"] = "outline" if geom["type"] != "Point" else "point"
        feats.append({"type": "Feature", "geometry": _round(geom), "properties": props})
    bb = [math.inf, math.inf, -math.inf, -math.inf]
    for f in feats:
        _grow(bb, f["geometry"]["coordinates"])
    about = ""
    for s in xl.sheet_names:  # GEM puts licence and citation notes on an "About" sheet
        if re.search(r"about|read ?me|licen", s, re.I):
            about = " ".join(str(x) for x in xl.parse(s, header=None).fillna("").values.ravel() if str(x).strip())[:4000]
            break
    print(f"{sheet}: {len(df):,} rows -> {len(feats):,} features ({n_outline:,} outlines; {n_bad} outlines not in lon/lat "
          f"or not near the row's point, so the point was used); {n_none:,} rows with no usable location left out")
    return {
        "type": "FeatureCollection",
        "atlas_source": {"publisher": spec["publisher"], "citation": spec.get("citation", ""), "licence": spec["licence"],
                         "release": spec.get("release", ""), "landing_page": spec.get("landing_page", ""),
                         "converted": date.today().isoformat(), "source_file": src.name, "sheet": sheet,
                         "rows": len(df), "rows_without_location": n_none},
        "bbox": [round(x, 6) for x in bb] if feats else None,
        "features": feats,
    }, about


def _round(g):
    def r(c):
        return [round(c[0], 5), round(c[1], 5)] if isinstance(c[0], (int, float)) else [r(x) for x in c]
    return {"type": g["type"], "coordinates": r(g["coordinates"])}


def _grow(bb, c):
    if isinstance(c[0], (int, float)):
        bb[0], bb[1], bb[2], bb[3] = min(bb[0], c[0]), min(bb[1], c[1]), max(bb[2], c[0]), max(bb[3], c[1])
    else:
        for x in c:
            _grow(bb, x)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("source", help="the publisher's file (.xlsx)")
    args = ap.parse_args()
    spec = yaml.safe_load(Path(args.spec).read_text())
    gj, about = convert(spec, Path(args.source))
    out = ROOT / "files" / f"{spec['id']}.geojson"
    out.write_text(json.dumps(gj, separators=(",", ":"), ensure_ascii=False))
    print(f"{out.relative_to(ROOT)}: {len(gj['features']):,} features, {out.stat().st_size / 1e6:.1f} MB, bbox {gj['bbox']}")
    if about:
        print("About sheet (check for licence exceptions):", about[:1500])
    # catalogue record for the spike-files wave
    seeds = ROOT / "vocab" / "seeds" / "files.yaml"
    doc = yaml.safe_load(seeds.read_text()) if seeds.exists() else {"defaults": {"publisher_type": "civil-society"}, "sources": []}
    doc["sources"] = [s for s in doc["sources"] if s.get("id") != spec["id"]]
    doc["sources"].append({
        "kind": "record", "id": spec["id"], "title": spec["title"], "publisher": spec["publisher"],
        "publisher_type": spec.get("publisher_type", "civil-society"),
        "abstract": spec["abstract"].strip() + (f" Release: {spec['release']}." if spec.get("release") else "")
                    + f" Hosted by the atlas as a copy of the publisher's download; cite as: {spec.get('citation', spec['publisher'])}.",
        "licence": spec["licence"], "landing_page": spec.get("landing_page", ""),
        "bbox": [round(x, 4) for x in gj["bbox"]],
        "geometry_type": "polygon" if any(f["geometry"]["type"] != "Point" for f in gj["features"]) else "point",
        "concepts_hint": spec.get("concepts_hint", []),
        "endpoints": [{"protocol": "geojson", "url": PAGES_BASE + f"{spec['id']}.geojson", "format": "GeoJSON"},
                      {"protocol": "landing", "url": spec.get("landing_page", "")}],
    })
    seeds.write_text("# Written by atlas/files.py from vocab/files/*.yaml: datasets the atlas hosts as files.\n"
                     + yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=120))
    print(f"catalogue record written to {seeds.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
