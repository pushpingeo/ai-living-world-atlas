"""Keep big parquet files under GitHub's 100 MB per-file limit on the results branches.

python -m atlas.parts split DIR             # any DIR/*.parquet over 90 MB becomes NAME-000.parquet, NAME-001.parquet ...
python -m atlas.parts get REF NAME OUT [COLS] # read NAME.parquet or its parts from git REF, write one file to OUT (only COLS, comma-separated)

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


def get(ref: str, name: str, out: Path, columns: list[str] | None = None) -> bool:
    """Write NAME's parts from git REF into one file, one part at a time.

    Europe's layers are ten parts of ~50 MB that expand to several GB in memory; concatenating them all at once
    was killed for lack of memory, and the fetch script then skipped the whole wave (17 Nov). Streaming part by
    part keeps memory to one part, and `columns` reads only what the caller needs.
    """
    files = subprocess.run(["git", "ls-tree", "--name-only", ref], capture_output=True, text=True, check=True).stdout.split()
    parts = sorted(f for f in files if f == f"{name}.parquet" or re.fullmatch(rf"{re.escape(name)}(-\d{{3}})+\.parquet", f))
    if not parts:
        return False
    with tempfile.TemporaryDirectory() as tmp:
        locals_ = []
        for f in parts:
            local = Path(tmp) / f
            local.write_bytes(subprocess.run(["git", "show", f"{ref}:{f}"], capture_output=True, check=True).stdout)
            if local.stat().st_size:
                locals_.append(local)
        if not locals_:
            return False
        schemas = [pq.read_schema(x) for x in locals_]
        schema = pa.unify_schemas(schemas, promote_options="default")
        if columns:
            schema = pa.schema([schema.field(c) for c in columns if c in schema.names], metadata=schema.metadata)
        schema = schema.with_metadata(schemas[0].metadata)
        with pq.ParquetWriter(out, schema, compression="zstd") as w:
            for x in locals_:
                pf = pq.ParquetFile(x)
                have = [c for c in schema.names if c in pf.schema_arrow.names]
                for i in range(pf.num_row_groups):
                    t = pf.read_row_group(i, columns=have)
                    for c in schema.names:  # columns a part lacks come through as nulls
                        if c not in t.column_names:
                            t = t.append_column(schema.field(c), pa.nulls(len(t), schema.field(c).type))
                    w.write_table(t.select(schema.names).cast(schema), row_group_size=100_000)
    return True


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "split":
        split(Path(sys.argv[2]))
    elif cmd == "get":
        cols = sys.argv[5].split(",") if len(sys.argv) > 5 and sys.argv[5] else None
        sys.exit(0 if get(sys.argv[2], sys.argv[3], Path(sys.argv[4]), cols) else 1)
    else:
        sys.exit(f"unknown command {cmd}")
