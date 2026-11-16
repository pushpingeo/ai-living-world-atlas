"""Combine published waves into one set of files for the viewer, the MCP database and tagging.

python -m atlas.combine --out /tmp/pub  datasets_a.parquet datasets_b.parquet ...  [--tags t1.parquet t2.parquet]
The first wave listed wins when the same dataset appears in two (e.g. EEA services found from the UK and the global list).
"""
from __future__ import annotations

import argparse
from pathlib import Path

import geopandas as gpd
import pandas as pd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("datasets", nargs="+")
    ap.add_argument("--tags", nargs="*", default=[])
    ap.add_argument("--layers", nargs="*", default=[])
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    ds = pd.concat([gpd.read_parquet(p) for p in a.datasets if Path(p).exists()], ignore_index=True)
    ds = gpd.GeoDataFrame(ds.drop_duplicates("dataset_id"), geometry="geometry", crs="EPSG:4326")
    ds.to_parquet(out / "datasets.parquet", write_covering_bbox=True, compression="zstd")
    if a.layers:
        cols = ["uid", "dataset_id", "fields"]
        ly = pd.concat([pd.read_parquet(p, columns=cols) for p in a.layers if Path(p).exists()], ignore_index=True)
        ly.drop_duplicates("uid").to_parquet(out / "layers.parquet")
    if a.tags:
        tg = pd.concat([pd.read_parquet(p) for p in a.tags if Path(p).exists()], ignore_index=True)
        # newest tagging wins
        tg = tg.sort_values("tagged_at").drop_duplicates("dataset_id", keep="last")
        tg.to_parquet(out / "tags.parquet")
    print(f"{len(ds)} datasets from {len(a.datasets)} waves; tags: {len(tg) if a.tags else 0}")


if __name__ == "__main__":
    main()
