"""Combine published waves into one set of files for the viewer, the MCP database and tagging.

python -m atlas.combine --out /tmp/pub  datasets_a.parquet datasets_b.parquet ...  [--tags t1.parquet t2.parquet]
The first wave listed wins when the same dataset appears in two (e.g. EEA services found from the UK and the global list).
"""
from __future__ import annotations

import argparse
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pyarrow.parquet as pq

from .hand_fixes import apply as fix_concepts
from .hand_fixes import publisher_types
from .licences import infer as infer_licences
from .licences import overrides as licence_overrides
from .sampling import add_sample
from .titles import fix_titles


def apply_liveness(ds, d: Path):
    """Fold the rolling liveness sweep into the published datasets.
    - Retired endpoints are removed; a dataset with none left is dropped.
    - Endpoints failing but not yet retired get "status": "failing" (nothing is added while they're fine, so the
      MCP database only sees writes when something actually changes).
    - The endpoint's "check" takes the latest sampled data check.
    - Publisher edits to a layer's title or description replace the dataset's text where it was that layer's text."""
    import json

    from .sweep import FAILING, patched_datasets

    st = pd.read_parquet(d / "state.parquet")
    if "data_detail" not in st.columns:
        st["data_detail"] = None
    retired = set(st.loc[st["retired"].astype(bool), "uid"])
    failing = set(st.loc[~st["retired"].astype(bool) & st["status"].isin(FAILING), "uid"])
    has = st["data_check"].notna() & (st["data_check"] != "")
    data = dict(zip(st.loc[has, "uid"], st.loc[has, "data_check"]))
    # ArcGIS layers that advertise Query but refused it when the sweep tried: drop "query" from that endpoint
    no_query = set(st.loc[st["data_detail"].astype(str).str.contains("query refused", regex=False), "uid"])
    new_eps, n_eps, protos, caps, keep = [], [], [], [], []
    dropped_eps = 0
    for eps_json, p0, c0, n0 in zip(ds["endpoints"], ds["protocols"], ds["capabilities"], ds["n_endpoints"]):
        eps = json.loads(eps_json)
        kept = [e for e in eps if e["uid"] not in retired]
        dropped_eps += len(eps) - len(kept)
        if len(kept) == len(eps) and not any(e["uid"] in failing or e.get("status") or data.get(e["uid"], e.get("check")) != e.get("check")
                                             or (e["uid"] in no_query and "query" in (e.get("capabilities") or [])) for e in eps):
            new_eps.append(eps_json); n_eps.append(n0); protos.append(p0); caps.append(c0); keep.append(True)
            continue
        for e in kept:
            if data.get(e["uid"]):
                e["check"] = data[e["uid"]]
            if e["uid"] in no_query and "query" in (e.get("capabilities") or []):
                e["capabilities"] = [x for x in e["capabilities"] if x != "query"]
                e["query_refused"] = True
            if e["uid"] in failing:
                e["status"] = "failing"
            else:
                e.pop("status", None)
        new_eps.append(json.dumps(kept, separators=(",", ":")))
        n_eps.append(int(n0) - (len(eps) - len(kept)))  # collections list 300 endpoints but count every plan
        if len(kept) == len(eps) and not any(e.get("query_refused") for e in kept):
            protos.append(p0); caps.append(c0)
        else:
            protos.append(list(dict.fromkeys(e["protocol"] for e in kept)))
            caps.append(sorted({c for e in kept for c in e.get("capabilities") or []}))
        keep.append(bool(kept))
    ds = ds.assign(endpoints=new_eps, n_endpoints=n_eps, protocols=protos, capabilities=caps)
    gone = (~pd.Series(keep, index=ds.index)).sum()
    ds = ds[keep]
    edits = 0
    if (d / "changes.parquet").exists():
        ch = pd.read_parquet(d / "changes.parquet")
        ch = ch[ch["dataset_id"].isin(set(ds["dataset_id"]))]
        if len(ch):
            tmp = Path("/tmp/_live_ds.parquet")
            ds.to_parquet(tmp)
            p = patched_datasets(str(tmp), ch)
            if len(p):
                p = p.set_index("dataset_id")
                idx = ds["dataset_id"].isin(p.index)
                ds.loc[idx, "title"] = ds.loc[idx, "dataset_id"].map(p["title"]).values
                ds.loc[idx, "abstract"] = ds.loc[idx, "dataset_id"].map(p["abstract"]).values
                edits = len(p)
    print(f"liveness: {dropped_eps} retired endpoints removed, {gone} datasets dropped, {len(failing)} endpoints failing, "
          f"{edits} datasets with publisher text edits", flush=True)
    return ds


def drop_covered(ds):
    """Drop a dataset whose endpoints all belong to a dataset from an earlier wave in runs/published.txt.

    A focused wave (e.g. spike-emodnet, which groups a layer's WFS and WMS) can find what a broad wave found as a
    WMS-only record; the grouped record gets a different id. Listing the focused wave first makes it win.
    """
    import json as _json
    seen, keep = set(), []
    for eps in ds["endpoints"]:
        try:
            u = {e.get("uid") for e in _json.loads(eps or "[]")} - {None, ""}
        except Exception:
            u = set()
        keep.append(not (u and u <= seen))
        seen |= u
    n = len(keep) - sum(keep)
    print(f"combine: {n:,} datasets dropped because an earlier wave's dataset already holds all their endpoints", flush=True)
    return ds[keep] if n else ds


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("datasets", nargs="+")
    ap.add_argument("--tags", nargs="*", default=[])
    ap.add_argument("--layers", nargs="*", default=[])
    ap.add_argument("--out", required=True)
    ap.add_argument("--only-passing", action="store_true", help="keep only datasets that pass the quality bar (and their layers)")
    ap.add_argument("--liveness", default="", help="results/liveness checkout: drop retired endpoints, apply text edits")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    flt = [("q_pass", "==", True)] if a.only_passing else None  # filter while reading: Europe alone is millions of rows
    ds = pd.concat([gpd.read_parquet(p, filters=flt) for p in a.datasets if Path(p).exists()], ignore_index=True)
    ds = gpd.GeoDataFrame(ds.drop_duplicates("dataset_id"), geometry="geometry", crs="EPSG:4326")
    ds = drop_covered(ds)
    if a.liveness and (Path(a.liveness) / "state.parquet").exists():
        ds = apply_liveness(ds, Path(a.liveness))
    ds, splits = fix_titles(ds)  # status words from service names; live and removed services split apart
    ds = infer_licences(ds)  # e.g. US federal works; the wave files keep what was crawled
    ds = licence_overrides(ds)  # hand-recorded licences, attribution lines and terms (vocab/licence_overrides.yaml)
    ds = add_sample(ds)  # capability "sample": endpoints that return a value at a point (vocab/sample_rules.yaml)
    ds = publisher_types(ds)  # by publisher name, where the host is shared (vocab/publisher_type_overrides.yaml)
    ds.to_parquet(out / "datasets.parquet", write_covering_bbox=True, compression="zstd")
    if a.layers:
        cols = ["uid", "dataset_id", "fields", "title", "abstract", "geometry_type"]  # title/abstract: the liveness sweep compares against them; geometry_type: the MCP search
        keep = set(ds["dataset_id"]) if a.only_passing else None
        lf = [("dataset_id", "in", keep)] if keep is not None else None
        ly = pd.concat([pd.read_parquet(p, columns=[c for c in cols if c in pq.read_schema(p).names], filters=lf) for p in a.layers if Path(p).exists()], ignore_index=True)
        ly = ly.drop_duplicates("uid")
        if splits:  # layers that moved to a split-off dataset follow it
            import json as _json
            moved = {e["uid"]: did for did, eps in zip(ds["dataset_id"], ds["endpoints"]) if did in splits
                     for e in _json.loads(eps) if e.get("uid")}
            ly["dataset_id"] = [moved.get(u, d) for u, d in zip(ly["uid"], ly["dataset_id"])]
        ly.to_parquet(out / "layers.parquet")
    if a.tags:
        tg = pd.concat([pd.read_parquet(p) for p in a.tags if Path(p).exists() and Path(p).stat().st_size > 0], ignore_index=True)
        # newest tagging wins
        tg = tg.sort_values("tagged_at", kind="stable").drop_duplicates("dataset_id", keep="last")
        if splits:  # a split-off dataset shares its parent's tags
            par = tg.set_index("dataset_id")
            add = [par.loc[o].to_dict() | {"dataset_id": n} for n, o in splits.items() if o in par.index]
            if add:
                tg = pd.concat([tg, pd.DataFrame(add)], ignore_index=True)
        tg = fix_concepts(tg, ds)  # hand-set concepts where the tagger misleads searches (vocab/concept_overrides.yaml)
        tg.to_parquet(out / "tags.parquet")
    print(f"{len(ds)} datasets from {len(a.datasets)} waves; tags: {len(tg) if a.tags else 0}")


if __name__ == "__main__":
    main()
