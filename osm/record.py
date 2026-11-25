"""The atlas record for one market's OpenStreetMap copy, from the manifest the build just published.

Writes (or replaces) the entry `osm-copy-<market>` in vocab/seeds/osm.yaml, which the `spike-osm` wave turns into a
dataset like any other: publisher OpenStreetMap contributors, ODbL 1.0, the data date, a coverage outline and the
manifest's URL. The abstract stays the same from week to week (no counts or dates in it), so a refresh needs no
re-tagging; what changes each week (release, data date, features, outline) goes in the endpoint info.

    python3 osm/record.py --market uk --manifest manifest.json --report report-uk.json \
        --url https://data.asktobler.com/osm/uk.json [--seeds vocab/seeds/osm.yaml]
"""
import argparse, json, os, sys
from pathlib import Path

import shapely
import yaml
from shapely.geometry import mapping, shape

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
COUNTRY = {"uk": "GB", "nl": "NL", "au": "AU", "us": "US"}
# Kinds named for people, per group (the spec's names, in the order a reader would look for them).
GROUP_WORDS = {
    "transport": "main roads (motorway, trunk, primary), railways and aerodromes",
    "utilities": "power lines, substations, pipelines and wind turbines",
    "water": "water bodies (lakes, reservoirs, basins) and watercourses (rivers, streams, canals, ditches, drains)",
    "landuse": "residential land",
    "community": "schools, colleges and nurseries, and hospitals, clinics and care homes",
    "buildings": "every building",
}
OUTLINE_MAX_CHARS = 6000  # the record keeps a coarse outline; the manifest has the exact one


def coarse_outline(outline):
    """A small copy of the manifest's outline for the record (searches and maps). Simplifying can move the edge a
    little either way, so the record says the manifest's outline is the one to test against."""
    if not outline:
        return None, None
    g = shape(outline)
    for tol in (0.02, 0.05, 0.1, 0.2, 0.5):
        s = g.simplify(tol, preserve_topology=True)
        if s.geom_type == "MultiPolygon":  # drop islands too small to see at this tolerance
            s = shapely.MultiPolygon([p for p in s.geoms if p.area > tol * tol * 4]) if any(p.area > tol * tol * 4 for p in s.geoms) else s
        m = mapping(s)
        def r(c):
            return [r(x) for x in c] if isinstance(c[0], (list, tuple)) else [round(c[0], 3), round(c[1], 3)]
        m = {"type": m["type"], "coordinates": r(m["coordinates"])}
        if len(json.dumps(m, separators=(",", ":"))) <= OUTLINE_MAX_CHARS:
            return m, tol
    return None, None


def entry(market, spec, manifest, report, url):
    mk = spec["markets"][market]
    groups = {}
    for kind, g in manifest["kind_groups"].items():
        groups.setdefault(g, []).append(kind)
    outline, tol = coarse_outline(manifest.get("outline"))
    bbox = [round(x, 4) for x in shape(manifest["outline"]).bounds] if manifest.get("outline") else None
    oldest = (manifest.get("data_as_of") or {}).get("oldest")
    by_group = (report or {}).get("by_group") or {}
    words = "; ".join(f"{g}: {GROUP_WORDS.get(g, ', '.join(groups.get(g, [])))}" for g in spec["groups"])
    abstract = (
        f"A copy of the OpenStreetMap features that site screening asks about, for {mk['name']}, hosted by the atlas "
        f"so checks don't depend on the public Overpass servers. Six files per Geofabrik extract, one per group: {words}. "
        "The tags are the same ones Tobler's Overpass queries use, so a lookup in the copy gives the same answer as a "
        "live query, as of the copy's data date. Areas are whole polygons, including multipolygon relations. Each file "
        "is FlatGeobuf with a packed Hilbert R-tree, so a reader fetches only the parts near a site with HTTP range "
        "requests, and GeoParquet 1.1 with a bbox column for DuckDB or QGIS. Start from the manifest (this endpoint): it "
        "lists every extract with its bounding box, data date and file paths (relative to the manifest), and the outline "
        "the copy covers, drawn about 1 km inside the extracts so it never claims ground it doesn't hold. Rebuilt weekly "
        "from Geofabrik. OpenStreetMap is mapped by volunteers: coverage is good for roads, railways and power lines, and "
        "uneven for buildings and land use. A feature missing here may exist on the ground."
    )
    info = {
        "manifest": url,
        "layout": "<market>.json is the manifest; files at <release>/<extract id>/<group>.fgb (and .parquet), relative to it. Contract: docs/mcp-tools.md, Hosted OpenStreetMap copy.",
        "groups": {g: groups.get(g, []) for g in spec["groups"]},
        "release": manifest["release"],
        "data_date": oldest[:10] if oldest else None,
        "data_date_source": "OpenStreetMap replication time of the oldest Geofabrik extract in this release",
        "data_as_of": manifest.get("data_as_of"),
        "extracts": len(manifest.get("regions") or []),
        "extracts_missing": manifest.get("missing") or [],
        "features": {g: v.get("features") for g, v in by_group.items()},
        "completeness": "partial",
        "completeness_note": "complete for the extracts listed (every feature with these tags); OpenStreetMap itself is volunteer-mapped and uneven, especially for buildings and land use. Extracts missing from a release are left out of its outline.",
        "attribution": "© OpenStreetMap contributors",
        "terms": "Open Database License 1.0: attribute OpenStreetMap contributors; a database made from it and shared must be shared under the ODbL too. Maps and other produced works need only the attribution.",
        "refresh": "weekly",
    }
    if outline:
        info["coverage_outline"] = outline
        info["coverage_outline_note"] = f"simplified ({tol} degrees) from the manifest's outline; test coverage against the manifest's"
    if (manifest.get("missing") or []):
        info["status_note"] = f"{len(manifest['missing'])} extracts didn't build in release {manifest['release']}; the copy's outline leaves them out"
    return {
        "kind": "record",
        "id": f"osm-copy-{market}",
        "title": f"OpenStreetMap copy for site checks: {mk['name']} (roads, rail, utilities, water, land use, community, buildings)",
        "publisher": "OpenStreetMap contributors",
        "publisher_type": "civil-society",
        "country": COUNTRY.get(market, ""),
        "abstract": abstract,
        "licence": "Open Database License (ODbL) 1.0. © OpenStreetMap contributors (https://www.openstreetmap.org/copyright).",
        "landing_page": "https://www.openstreetmap.org/copyright",
        "bbox": bbox,
        "concepts_hint": ["road", "rail", "port-airport", "power-line", "pipeline", "power-plant", "river", "settlement",
                          "school", "health-facility", "building"],
        "endpoints": [
            {"protocol": "cloud", "url": url, "format": "FlatGeobuf and GeoParquet, with a JSON manifest", "info": info},
            {"protocol": "landing", "url": "https://www.openstreetmap.org/copyright"},
        ],
    }


HEADER = """# Written by osm/record.py after each OpenStreetMap copy build (.github/workflows/osm.yml): one record per market
# copy the atlas hosts in the R2 bucket atlas-data. Don't edit by hand; change osm/record.py instead.
"""


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--market", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--report")
    ap.add_argument("--url", required=True, help="the manifest's public URL")
    ap.add_argument("--seeds", default=str(ROOT / "vocab" / "seeds" / "osm.yaml"))
    a = ap.parse_args(argv)
    spec = json.load(open(HERE / "spec.json"))
    manifest = json.load(open(a.manifest))
    report = json.load(open(a.report)) if a.report and os.path.exists(a.report) else None
    if not manifest.get("regions"):
        print("no extracts in the manifest; record left as it was")
        return 1
    p = Path(a.seeds)
    doc = yaml.safe_load(p.read_text()) if p.exists() else None
    doc = doc or {"defaults": {"publisher_type": "civil-society"}, "sources": []}
    new = entry(a.market, spec, manifest, report, a.url)
    doc["sources"] = [s for s in doc.get("sources") or [] if s.get("id") != new["id"]] + [new]
    doc["sources"].sort(key=lambda s: s["id"])
    p.write_text(HEADER + yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=120))
    print(f"{new['id']}: release {manifest['release']}, data date {new['endpoints'][0]['info']['data_date']}, "
          f"{new['endpoints'][0]['info']['extracts']} extracts, outline "
          f"{'kept' if 'coverage_outline' in new['endpoints'][0]['info'] else 'too big, left to the manifest'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
