"""Group the long tail of local development plans into one collection per council.

European catalogues publish every local development or land-use plan (Bebauungsplan, PLU, bestemmingsplan,
UPU/PPUO ...) as its own service, so one wave can hold hundreds of thousands of near-identical entries
("SpatialPlan", "OfficialDocumentation", "Raster"). They are authoritative but drown everything else.
Here each council's plans become one dataset ("Development plans – Stadt Stuttgart, 1,768 plans") that lists
their services as endpoints. The individual plans stay in the files, marked as members (q_pass false,
flag in-collection, collection_id set) so the viewer, the MCP server and tagging skip them.

python -m atlas.collections --datasets wave_datasets.parquet --out DIR
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import box

from .resolution import coverage_level

# Words that mark a local plan, in the languages that publish them in bulk. Matched on title, start of the
# abstract and the licence/constraints text (German councils often state "Inhalt der Bebauungspläne" there).
PLAN = re.compile(
    r"spatial ?plan|officialdocumentation|planned land use|land[- ]use plan|development plan|zoning plan|"
    r"bebauungspl|\bB-?Plan\b|\bBPL\b|xplan|fl[aä]chennutzungspl|\bFNP\b|fl[aä]chenwidmungspl|rasterplan|"
    r"geltungsbereich|baugrenze|baugebiet|[uü]berbaubare|nutzungsplan|planteil|"
    r"plan local d.urbanisme|\bPLU[iI]?\b|carte communale|bestemmingsplan|piano regolatore|\bPRG\b|"
    r"\b(?:UPU|PPUO|PPUG|GUP|DPU)\b|urbanisti[cč]k\w* plan|prostorn\w* plan",
    re.I,
)
DEMO_PUBLISHER = re.compile(r"testhausen|musterstadt|mustergemeinde|beispielstadt|demo", re.I)  # XPlanung sample councils
MIN_GROUP = 3  # councils with fewer plans keep them as individual entries
MAX_LISTED = 300  # endpoints listed on a collection; the rest are counted


def service_key(url: str) -> str:
    """The service an endpoint belongs to: URL without query, layer index or layer path."""
    u = urlsplit(url or "")
    path = re.sub(r"/\d+$", "", u.path.rstrip("/"))
    m = re.search(r"^(.*?_(wms|wfs|wmts))(/|$)", path, re.I)  # haleconnect-style .../<id>_wfs/<layer>
    if m:
        path = m.group(1)
    return f"{u.netloc.lower()}{path.lower()}"


def _keys(endpoints: str) -> list[str]:
    try:
        return sorted({service_key(e.get("url", "")) for e in json.loads(endpoints or "[]")})
    except ValueError:
        return []


def collection_row(g: gpd.GeoDataFrame, publisher: str, country: str) -> dict:
    n = len(g)
    b = g.total_bounds
    bbox = [float(x) for x in b]
    names = [t for t in g["title"].dropna() if not PLAN.fullmatch(t.strip()) and len(t) > 6 and not re.fullmatch(r"(?i)raster|bereich", t)]
    eps, total = [], 0
    for title, e in zip(g["title"], g["endpoints"]):
        for x in json.loads(e or "[]"):
            total += 1
            if len(eps) < MAX_LISTED:
                eps.append({**x, "plan": title})
    lic = Counter(x for x in g["licence"].fillna("") if x).most_common(1)
    did = "c" + hashlib.sha1(f"plans|{country}|{publisher}".encode()).hexdigest()[:15]
    sample = "; ".join(dict.fromkeys(names))[:400]
    return {
        "dataset_id": did,
        "title": f"Development plans – {publisher}",
        "abstract": (f"{n} local development and land-use plans published by {publisher} ({country}) as separate map "
                     f"services, typically INSPIRE Planned Land Use or XPlanung. This entry groups them; each plan's "
                     f"services are listed as endpoints{f' (first {MAX_LISTED} of {total})' if total > MAX_LISTED else ''}."
                     + (f" Plans include: {sample}." if sample else "")),
        "publisher": publisher, "publisher_type": g["publisher_type"].mode().iat[0], "country": country,
        "licence": lic[0][0] if lic else "", "open_licence": bool(g["open_licence"].any()),
        "keywords": ["development plan", "land use plan", "planned land use"],
        "iso_themes_declared": ["planningCadastre"], "landing_page": "",
        "role": "data", "coverage_level": coverage_level(bbox) or "local", "extent_source": "members",
        "extent_flags": [], "detail_m": float(g["detail_m"].median()) if g["detail_m"].notna().any() else np.nan,
        "detail_level": "", "detail_source": "",
        "protocols": sorted({p for v in g["protocols"] for p in (v if v is not None else [])}),
        "capabilities": sorted({p for v in g["capabilities"] for p in (v if v is not None else [])}),
        "n_endpoints": total, "match_rules": ["collection"], "q_total": int(g["q_total"].median()), "q_pass": True,
        "endpoints": json.dumps(eps, separators=(",", ":")),
        "collection_id": "", "collection_size": n,
        "geometry": box(*b),
    }


def main():
    import pyarrow as pa
    import pyarrow.parquet as pq

    ap = argparse.ArgumentParser()
    ap.add_argument("--datasets", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    src = pq.ParquetFile(a.datasets)

    # pass 1, a row group at a time: which datasets read as plans, and which services they sit on
    cols = ["dataset_id", "title", "abstract", "licence", "endpoints", "q_pass", "country", "publisher"]
    ids, plan, keys, passing, grp = [], [], [], [], []
    for rb in src.iter_batches(batch_size=100_000, columns=cols):
        b = rb.to_pandas()
        text = b["title"].fillna("") + " " + b["abstract"].fillna("").str[:400] + " " + b["licence"].fillna("").str[:200]
        ids += list(b["dataset_id"]); plan += list(text.str.contains(PLAN)); keys += list(b["endpoints"].map(_keys))
        passing += list(b["q_pass"].astype(bool)); grp += list(zip(b["country"].fillna(""), b["publisher"].fillna("")))
    # a service counts as a plan service only if most of what it serves reads as plans: national services that
    # carry one zoning layer among hundreds (swisstopo, Scottish Government) must not drag the rest in
    tot, hit = Counter(), Counter()
    for ks, p in zip(keys, plan):
        for k in ks:
            tot[k] += 1
            hit[k] += bool(p)
    plan_services = {k for k in tot if hit[k] >= 0.5 * tot[k]}
    del tot, hit
    seen, counts = set(), Counter()
    is_member_cand = {}
    for did, p, ks, ok, g in zip(ids, plan, keys, passing, grp):
        if did in seen:
            continue
        seen.add(did)
        if ok and (p or any(k in plan_services for k in ks)):
            is_member_cand[did] = g
            counts[g] += 1
    n_plans = sum(1 for did, p, ks in zip(ids, plan, keys) if p or any(k in plan_services for k in ks))
    del keys, plan_services
    demo = {did for did, g in is_member_cand.items() if DEMO_PUBLISHER.search(g[1])}
    groups = {g for g, n in counts.items() if n >= MIN_GROUP and g[1] and not DEMO_PUBLISHER.search(g[1])}
    cid = {g: "c" + hashlib.sha1(f"plans|{g[0]}|{g[1]}".encode()).hexdigest()[:15] for g in groups}
    member_of = {did: cid[g] for did, g in is_member_cand.items() if g in groups}

    # pass 2: build each collection from its members' full rows
    full = gpd.read_parquet(a.datasets, filters=[("dataset_id", "in", list(member_of))]).drop_duplicates("dataset_id")
    full["_c"] = full["dataset_id"].map(member_of)
    rows = []
    for (country, publisher), g in full.groupby(["country", "publisher"], sort=False):
        rows.append(collection_row(g, str(publisher), str(country)))
    del full

    # pass 3: stream the wave through, marking members, then append the collections
    schema = src.schema_arrow.append(pa.field("collection_id", pa.string())).append(pa.field("collection_size", pa.int64()))
    w = pq.ParquetWriter(out / "datasets.parquet", schema, compression="zstd")
    done, kept = set(), 0
    for rb in src.iter_batches(batch_size=100_000):
        b = rb.to_pandas()
        first = ~b["dataset_id"].isin(done) & ~b["dataset_id"].duplicated()
        b = b[first]
        done.update(b["dataset_id"])
        c = b["dataset_id"].map(member_of).fillna("")
        m = c != ""
        dm = b["dataset_id"].isin(demo)
        b["q_pass"] = b["q_pass"].astype(bool) & ~m & ~dm
        b.loc[dm, "extent_flags"] = b.loc[dm, "extent_flags"].map(lambda v: list(v if v is not None else []) + ["demo-data"])
        b.loc[m, "extent_flags"] = b.loc[m, "extent_flags"].map(lambda v: list(v if v is not None else []) + ["in-collection"])
        b["collection_id"] = c
        b["collection_size"] = 0
        w.write_table(pa.Table.from_pandas(b, schema=schema, preserve_index=False))
        kept += len(b)
    coll = gpd.GeoDataFrame(pd.DataFrame(rows), geometry="geometry", crs="EPSG:4326")
    coll["bbox"] = [{"xmin": float(x[0]), "ymin": float(x[1]), "xmax": float(x[2]), "ymax": float(x[3])} for x in coll.geometry.bounds.values]
    cdf = pd.DataFrame(coll.drop(columns="geometry"))
    cdf["geometry"] = coll.geometry.to_wkb()
    w.write_table(pa.Table.from_pandas(cdf[schema.names], schema=schema, preserve_index=False))
    w.close()

    stats = {"datasets_in": len(seen), "plans_detected": n_plans, "plans_passing": len(is_member_cand),
             "collections": len(rows), "members_grouped": len(member_of)}
    pa_after = pq.read_table(out / "datasets.parquet", columns=["q_pass"]).column(0).to_pylist()
    stats["passing_after"] = int(sum(bool(x) for x in pa_after))
    stats["passing_before"] = stats["passing_after"] - len(rows) + len(member_of)
    (out / "collections.json").write_text(json.dumps(stats, indent=1))
    top = sorted(rows, key=lambda r: -r["collection_size"])[:15]
    lines = ["# Development-plan collections\n",
             f"- {stats['plans_detected']:,} datasets look like local plans; {stats['plans_passing']:,} of them passed the quality bar.",
             f"- Grouped {stats['members_grouped']:,} of those into **{len(rows):,} collections** (one per council, {MIN_GROUP}+ plans).",
             f"- Passing datasets: {stats['passing_before']:,} before, **{stats['passing_after']:,} after**.\n",
             "Largest collections:\n"] + [f"- {r['title']} ({r['country']}): {r['collection_size']:,} plans" for r in top]
    (out / "COLLECTIONS.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
