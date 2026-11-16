"""Keep big parquet files under GitHub's 100 MB per-file limit on the results branches.

python -m atlas.parts split DIR             # any DIR/*.parquet over 90 MB becomes NAME-000.parquet, NAME-001.parquet ...
python -m atlas.parts get REF NAME OUT      # read NAME.parquet or its parts from git REF, write one file to OUT

Parts are row slices of the same table, written with the same schema metadata (so GeoParquet 'geo' survives).
"""
from __future__ import annotations

import math
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

LIMIT = 90 * 1024 * 1024


def split(d: Path, limit: int = LIMIT) -> None:
    for p in sorted(d.glob("*.parquet")):
        size = p.stat().st_size
        if size <= limit:
            continue
        t = pq.read_table(p)
        n = math.ceil(size / (limit * 0.8))  # margin: slices don't compress evenly
        step = math.ceil(t.num_rows / n)
        for i in range(n):
            pq.write_table(t.slice(i * step, step), d / f"{p.stem}-{i:03d}.parquet", compression="zstd")
        p.unlink()
        print(f"{p.name}: {size / 1e6:.0f} MB -> {n} parts", flush=True)


def get(ref: str, name: str, out: Path) -> bool:
    files = subprocess.run(["git", "ls-tree", "--name-only", ref], capture_output=True, text=True, check=True).stdout.split()
    parts = sorted(f for f in files if f == f"{name}.parquet" or re.fullmatch(rf"{re.escape(name)}-\d{{3}}\.parquet", f))
    if not parts:
        return False
    tables = []
    with tempfile.TemporaryDirectory() as tmp:
        for f in parts:
            local = Path(tmp) / f
            local.write_bytes(subprocess.run(["git", "show", f"{ref}:{f}"], capture_output=True, check=True).stdout)
            if local.stat().st_size:
                tables.append(pq.read_table(local))
    if not tables:
        return False
    t = pa.concat_tables(tables, promote_options="default")
    pq.write_table(t.replace_schema_metadata(tables[0].schema.metadata), out, compression="zstd")
    return True


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "split":
        split(Path(sys.argv[2]))
    elif cmd == "get":
        sys.exit(0 if get(sys.argv[2], sys.argv[3], Path(sys.argv[4])) else 1)
    else:
        sys.exit(f"unknown command {cmd}")
