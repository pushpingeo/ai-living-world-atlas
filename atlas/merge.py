"""Merge the outputs of sharded crawl jobs into one result: layers deduplicated, datasets regrouped
across shards (the same data can be found through two catalogues that landed in different shards).

python -m atlas.merge --name us --out out shard0/ shard1/ ...
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import SimpleNamespace

import geopandas as gpd
import numpy as np
import pandas as pd

from .spike import write_outputs


def _lists(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.columns:
        sample = next((v for v in df[col] if v is not None and not (isinstance(v, float) and v != v)), None)
        if isinstance(sample, np.ndarray):
            df[col] = df[col].apply(lambda v: [] if v is None or (isinstance(v, float) and v != v) else list(v))
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--name", required=True)
    ap.add_argument("--out", default="out")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    frames, svc, roots, portals, http, logs, minutes = [], [], [], [], {}, [], 0.0
    for d in map(Path, args.dirs):
        if not (d / "layers.parquet").exists():
            logs.append(f"{d.name}: no layers.parquet (shard failed or found nothing)")
            continue
        g = gpd.read_parquet(d / "layers.parquet")
        df = pd.DataFrame(g.drop(columns="geometry"))
        df["bbox"] = [list(x.bounds) if x is not None and not x.is_empty else None for x in g.geometry]
        frames.append(_lists(df.drop(columns=[c for c in ("dataset_id", "dataset_match") if c in df.columns])))
        if (d / "services.parquet").exists():
            svc += pd.read_parquet(d / "services.parquet").to_dict("records")
        for f, acc in (("roots.json", roots), ("portals.json", portals)):
            if (d / f).exists():
                acc += json.loads((d / f).read_text())
        if (d / "stats.json").exists():
            st = json.loads((d / "stats.json").read_text())
            minutes = max(minutes, st.get("minutes", 0))
            for k, v in (st.get("http") or {}).items():
                http[k] = http.get(k, 0) + v
        if (d / "run.log").exists():
            logs.append(f"--- {d.name}\n" + (d / "run.log").read_text())
    rows = pd.concat(frames, ignore_index=True).drop_duplicates("uid").to_dict("records") if frames else []
    write_outputs(out, rows, svc, roots, portals, http, logs,
                  SimpleNamespace(countries=[args.name.upper()], seeds=[]), minutes * 60)
    print((out / "REPORT.md").read_text()[:1500])


if __name__ == "__main__":
    main()
