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
    xl = pd.ExcelFile(src)
    sheet, df = find_sheet(xl, spec)
    lat = next(c for c in df.columns if LAT.match(c))
    lon = next(c for c in df.columns if LON.match(c))
    keep = spec.get("columns") or [c for c in df.columns if c not in (lat, lon)]
    df = df.dropna(subset=[lat, lon])
    df = df[(df[lat].astype(float).abs() <= 90) & (df[lon].astype(float).abs() <= 180)]
    feats = [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [round(float(r[lon]), 6), round(float(r[lat]), 6)]},
              "properties": {k: clean(r.get(k)) for k in keep if k in df.columns}} for _, r in df.iterrows()]
    xs = [f["geometry"]["coordinates"][0] for f in feats]
    ys = [f["geometry"]["coordinates"][1] for f in feats]
    about = ""
    for s in xl.sheet_names:  # GEM puts licence and citation notes on an "About" sheet
        if re.search(r"about|read ?me|licen", s, re.I):
            about = " ".join(str(x) for x in xl.parse(s, header=None).fillna("").values.ravel() if str(x).strip())[:4000]
            break
    return {
        "type": "FeatureCollection",
        "atlas_source": {"publisher": spec["publisher"], "citation": spec.get("citation", ""), "licence": spec["licence"],
                         "release": spec.get("release", ""), "landing_page": spec.get("landing_page", ""),
                         "converted": date.today().isoformat(), "source_file": src.name, "sheet": sheet},
        "bbox": [min(xs), min(ys), max(xs), max(ys)] if feats else None,
        "features": feats,
    }, about


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
        "bbox": [round(x, 4) for x in gj["bbox"]], "geometry_type": "point",
        "concepts_hint": spec.get("concepts_hint", []),
        "endpoints": [{"protocol": "geojson", "url": PAGES_BASE + f"{spec['id']}.geojson", "format": "GeoJSON"},
                      {"protocol": "landing", "url": spec.get("landing_page", "")}],
    })
    seeds.write_text("# Written by atlas/files.py from vocab/files/*.yaml: datasets the atlas hosts as files.\n"
                     + yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=120))
    print(f"catalogue record written to {seeds.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
