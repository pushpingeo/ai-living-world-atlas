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


def stream_concat(files: list[Path], out: Path, stem: str, limit: int = 80 * 1024 * 1024) -> int:
    """Append shard parquet files into STEM-000.parquet, STEM-001.parquet ... one shard in memory at a time."""
    import json as _json
    import pyarrow as pa
    import pyarrow.parquet as pq

    files = [f for f in files if f.exists()]
    if not files:
        return 0
    schema = pa.unify_schemas([pq.read_schema(f) for f in files], promote_options="permissive")
    meta = dict(pq.read_schema(files[0]).metadata or {})
    if b"geo" in meta:  # per-file bbox in the GeoParquet metadata would be wrong for the merged file
        geo = _json.loads(meta[b"geo"])
        for col in geo.get("columns", {}).values():
            col.pop("bbox", None)
        meta[b"geo"] = _json.dumps(geo).encode()
    schema = schema.with_metadata(meta)
    part, rows, writer = 0, 0, None
    for f in files:
        pf = pq.ParquetFile(f)
        for i in range(pf.num_row_groups):
            t = pf.read_row_group(i)
            t = pa.Table.from_arrays([t[c].cast(schema.field(c).type) if c in t.column_names else pa.nulls(len(t), schema.field(c).type)
                                      for c in schema.names], schema=schema)
            if writer is None:
                path = out / f"{stem}-{part:03d}.parquet"
                writer = pq.ParquetWriter(path, schema, compression="zstd")
            writer.write_table(t, row_group_size=50_000)
            rows += len(t)
            if path.stat().st_size > limit:
                writer.close()
                writer, part = None, part + 1
    if writer:
        writer.close()
    return rows


def concat_merge(args, out: Path) -> None:
    """For waves too big to regroup in memory (Europe): keep each shard's datasets as they are and stream the
    files together. Datasets that span two shards stay as two; that only affects the same data found on two hosts."""
    dirs = list(map(Path, args.dirs))
    n_layers = stream_concat([d / "layers.parquet" for d in dirs], out, "layers")
    n_ds = stream_concat([d / "datasets.parquet" for d in dirs], out, "datasets")
    svc = [pd.read_parquet(d / "services.parquet") for d in dirs if (d / "services.parquet").exists()]
    if svc:
        pd.concat(svc, ignore_index=True).to_parquet(out / "services.parquet")
    roots, portals, totals, reports, logs = [], {}, {}, [], []
    for d in dirs:
        if (d / "roots.json").exists():
            roots += json.loads((d / "roots.json").read_text())
        if (d / "portals.json").exists():
            for p in json.loads((d / "portals.json").read_text()):
                portals[p.get("portal")] = p
        if (d / "stats.json").exists():
            st = json.loads((d / "stats.json").read_text())
            for k, v in (st.get("datasets") or {}).items():
                if isinstance(v, (int, float)):
                    totals[k] = totals.get(k, 0) + v
        if (d / "REPORT.md").exists():
            reports.append(f"## {d.name}\n\n" + (d / "REPORT.md").read_text().split("\n", 1)[1])
        if (d / "run.log").exists():
            logs.append(f"--- {d.name}\n" + (d / "run.log").read_text())
        elif not (d / "layers.parquet").exists():
            logs.append(f"{d.name}: no layers.parquet (shard failed or found nothing)")
    (out / "roots.json").write_text(json.dumps(roots))
    (out / "portals.json").write_text(json.dumps(list(portals.values())))
    (out / "run.log").write_text("\n".join(logs))
    stats = {"merge": "concat", "layers": n_layers, "datasets": {**totals, "count": n_ds}}
    (out / "stats.json").write_text(json.dumps(stats, indent=1, default=str))
    head = (f"# Spike report: {args.name.upper()} (concatenated shards)\n\n"
            f"- **Layers: {n_layers}; datasets: {n_ds}**; dataset totals summed over shards: {json.dumps(totals)}\n"
            f"- Shards were not regrouped against each other (too big to hold in memory), so a dataset published "
            f"on two hosts in different shards appears twice.\n\nPer-shard reports follow.\n\n")
    (out / "REPORT.md").write_text(head + "\n".join(reports))
    print(head)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--name", required=True)
    ap.add_argument("--out", default="out")
    ap.add_argument("--concat", action="store_true", help="stream shards together without regrouping (very large waves)")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if args.concat:
        return concat_merge(args, out)

    frames, svc, roots, portals, http, logs, minutes = [], [], [], [], {}, [], 0.0
    for d in map(Path, args.dirs):
        if (d / "layers.parquet").exists():
            g = gpd.read_parquet(d / "layers.parquet")
            df = pd.DataFrame(g.drop(columns="geometry"))
            df["bbox"] = [list(x.bounds) if x is not None and not x.is_empty else None for x in g.geometry]
            frames.append(_lists(df.drop(columns=[c for c in ("dataset_id", "dataset_match") if c in df.columns])))
        else:
            logs.append(f"{d.name}: no layers.parquet (shard failed or found nothing)")
            if (d / "crawl.log").exists():
                logs.append((d / "crawl.log").read_text()[-4000:])
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
