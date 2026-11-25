"""The atlas's hosted copy of OpenStreetMap: one OSM extract (a Geofabrik .osm.pbf) into one file per group of kinds.
Moved from Tobler's scripts/osm-extract/ on 25 Nov 2026; the same features, written by streaming since (see build()).

Keeps only the kinds in osm/spec.json (a copy of Tobler's catalogue/osm-snapshot.json; osm/check_spec.py fails the
build if Tobler's kinds and tags differ from it), with the same tags Tobler's Overpass query asks for, so a lookup in
the copy and a live Overpass query give the same answer (the copy is as old as the extract). Each group is written as
FlatGeobuf with its spatial index (what the browser reads: a few small range requests per site) and, with --parquet,
as GeoParquet 1.1 with a bbox column (for DuckDB, QGIS and the atlas). Both are sorted along a Hilbert curve, so
features near each other on the ground sit near each other in the file.

Areas are built properly: a closed way or a multipolygon relation becomes a (multi)polygon, where Overpass's "out
center" gave a relation only a centre point. Run on the output of `osmium tags-filter` (see filter_expressions) to
keep memory small; it also works on a whole extract.

    python3 osm/build.py --pbf wales.osm.pbf --region wales --out out/wales [--parquet]
"""
import argparse, json, os, sys, time
from datetime import datetime, timezone

# osmium, shapely, pyarrow and pyogrio are imported where they're used, so plan.py and publish.py (which only need
# the spec) run without them.

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC_PATH = os.path.join(HERE, "spec.json")


def load_spec(path=SPEC_PATH):
    with open(path) as f:
        return json.load(f)


def filter_expressions(spec):
    """Expressions for `osmium tags-filter` (one per tag key, values joined): a coarse first cut that keeps every
    object any kind could match, plus the nodes and members they need. The exact test is matches() below."""
    by = {}
    for k in spec["kinds"].values():
        types = "".join(sorted(set(k["types"].replace("a", "wr"))))
        for alt in k["match"]:
            key, val = next(iter(alt.items()))  # the first tag is enough to filter on; matches() checks all of them
            e = by.setdefault(key, {"types": set(), "values": set(), "any": False})
            e["types"].update(types)
            if val is True: e["any"] = True
            else: e["values"].update(val if isinstance(val, list) else [val])
    out = []
    for key, e in sorted(by.items()):
        t = "".join(sorted(e["types"]))
        out.append(f"{t}/{key}" if e["any"] else f"{t}/{key}=" + ",".join(sorted(e["values"])))
    return out


def tag_ok(tags, key, want):
    v = tags.get(key)
    if v is None: return False
    if want is True: return v != "no"
    return v in want if isinstance(want, list) else v == want


def matches(spec, tags, kind_type):
    """The kinds (name, def) whose match and types allow this object. kind_type: n, w or a."""
    out = []
    for name, k in spec["kinds"].items():
        if kind_type not in k["types"]: continue
        if any(all(tag_ok(tags, key, want) for key, want in alt.items()) for alt in k["match"]):
            out.append((name, k))
    return out


def kept_tags(spec, tags):
    keep = spec["keep_tags"]
    return {k: tags[k] for k in keep if k in tags}


CHUNK = 200_000  # features held in memory per group before they go to disk


def build(pbf, region, out_dir, spec=None, parquet=False, source_bytes=None, log=print):
    """Streams: features go to a compressed Arrow file per group in chunks while the extract is read, then GDAL writes
    the FlatGeobuf from that file batch by batch (with SPATIAL_INDEX it Hilbert-sorts the features itself, keeping only
    the index in memory), and the GeoParquet is written batch by batch from the sorted FlatGeobuf. Memory stays near
    one chunk per group, whatever the extract's size. (Tobler's first version held every feature in Python lists and a
    GeoDataFrame: 7.4 GB for Ireland's 418 MB extract, too much for Texas or California on a 16 GB runner.)"""
    import osmium
    import pyarrow as pa
    import pyogrio
    spec = spec or load_spec()
    t0 = time.time()
    os.makedirs(out_dir, exist_ok=True)
    schema = pa.schema([("osm_type", pa.string()), ("osm_id", pa.int64()), ("tags", pa.string()), ("geometry", pa.binary())])
    tmp = {g: os.path.join(out_dir, f".{g}.arrow") for g in spec["groups"]}
    writers = {g: pa.ipc.new_file(tmp[g], schema, options=pa.ipc.IpcWriteOptions(compression="lz4")) for g in spec["groups"]}
    bufs = {g: ([], [], [], []) for g in spec["groups"]}
    counts = {g: 0 for g in spec["groups"]}
    keys = sorted({key for k in spec["kinds"].values() for alt in k["match"] for key in alt})
    factory = osmium.geom.WKBFactory()
    skipped = {"bad_geometry": 0}

    def flush(g):
        b = bufs[g]
        if b[0]:
            writers[g].write_batch(pa.record_batch([pa.array(b[0], pa.string()), pa.array(b[1], pa.int64()), pa.array(b[2], pa.string()), pa.array(b[3], pa.binary())], schema=schema))
            for x in b: x.clear()

    def add(obj_type, obj_id, tags, geom_wkb, kinds):
        seen = set()
        for _, k in kinds:
            g = k["group"]
            if g in seen: continue
            seen.add(g)
            b = bufs[g]
            b[0].append(obj_type); b[1].append(obj_id); b[2].append(json.dumps(kept_tags(spec, tags), ensure_ascii=False)); b[3].append(bytes.fromhex(geom_wkb))
            counts[g] += 1
            if len(b[0]) >= CHUNK: flush(g)

    fp = osmium.FileProcessor(pbf).with_locations().with_areas().with_filter(osmium.filter.KeyFilter(*keys))
    for obj in fp:
        tags = dict(obj.tags)
        try:
            if obj.is_node():
                ks = matches(spec, tags, "n")
                if ks: add("node", obj.id, tags, factory.create_point(obj), ks)
            elif obj.is_way():
                closed = obj.is_closed()
                # A line kind keeps its line, closed or not. Other kinds: an open way stays a line (as Overpass gives
                # it); a closed one arrives again as an area below.
                ks = [(n, k) for n, k in matches(spec, tags, "w") if k.get("line") or not closed]
                if ks: add("way", obj.id, tags, factory.create_linestring(obj), ks)
            elif obj.is_area():
                ks = [(n, k) for n, k in matches(spec, tags, "a") if not k.get("line")]
                if ks: add("way" if obj.from_way() else "relation", obj.orig_id(), tags, factory.create_multipolygon(obj), ks)
        except (osmium.InvalidLocationError, RuntimeError):
            skipped["bad_geometry"] += 1
    for g in spec["groups"]:
        flush(g)
        writers[g].close()
    del fp
    read_s = time.time() - t0

    header = osmium.io.Reader(pbf, osmium.osm.osm_entity_bits.NOTHING)
    data_as_of = header.header().get("osmosis_replication_timestamp") or None
    header.close()

    stats = {"region": region, "data_as_of": data_as_of, "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
             "spec_version": spec["version"], "source_bytes": source_bytes or os.path.getsize(pbf), "filtered_bytes": os.path.getsize(pbf), "read_s": round(read_s, 1), "skipped": skipped, "groups": {}}
    for g in spec["groups"]:
        t1 = time.time()
        fgb = os.path.join(out_dir, f"{g}.fgb")
        with pa.memory_map(tmp[g]) as src:
            r = pa.ipc.open_file(src)
            batches = (r.get_batch(i) for i in range(r.num_record_batches))
            reader = pa.RecordBatchReader.from_batches(schema, batches)
            # Mixed points, lines and polygons in one file: FlatGeobuf allows it (geometry type Unknown).
            pyogrio.write_arrow(reader, fgb, driver="FlatGeobuf", geometry_name="geometry", geometry_type="Unknown", crs="EPSG:4326",
                                layer_options={"SPATIAL_INDEX": "YES", "TITLE": f"OpenStreetMap {g}, {region}"})
        os.remove(tmp[g])
        s = {"features": counts[g], "fgb_bytes": os.path.getsize(fgb)}
        if parquet:
            pq_path = os.path.join(out_dir, f"{g}.parquet")
            s["parquet_bytes"], bbox = write_parquet(fgb, pq_path)
            if bbox: s["bbox"] = bbox
        elif counts[g]:
            info = pyogrio.read_info(fgb)
            if info.get("total_bounds") is not None: s["bbox"] = [round(float(x), 5) for x in info["total_bounds"]]
        s["write_s"] = round(time.time() - t1, 1)
        stats["groups"][g] = s
        log(f"{region} {g}: {s['features']} features, {s['fgb_bytes'] / 1e6:.1f} MB fgb" + (f", {s.get('parquet_bytes', 0) / 1e6:.1f} MB parquet" if parquet else ""))
    stats["total_s"] = round(time.time() - t0, 1)
    # Peak memory of this process (Linux reports kB), to size the US build (California and Texas buildings).
    import resource
    stats["max_rss_mb"] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024)
    with open(os.path.join(out_dir, "stats.json"), "w") as f:
        json.dump(stats, f, indent=1)
    return stats


def write_parquet(fgb, path, row_group_size=20000):
    """GeoParquet 1.1 (WKB geometry, a bbox covering column, zstd) from a FlatGeobuf, in its order (Hilbert, when it
    has a spatial index), one batch at a time. Returns (bytes, total bbox or None)."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    import pyogrio
    import shapely
    geo = {"version": "1.1.0", "primary_column": "geometry",
           "columns": {"geometry": {"encoding": "WKB", "geometry_types": [],
                                    "covering": {"bbox": {"xmin": ["bbox", "xmin"], "ymin": ["bbox", "ymin"], "xmax": ["bbox", "xmax"], "ymax": ["bbox", "ymax"]}}}},
           "creator": {"library": "ai-living-world-atlas osm/build.py"}}
    bbox_t = pa.struct([("xmin", pa.float64()), ("ymin", pa.float64()), ("xmax", pa.float64()), ("ymax", pa.float64())])
    schema = pa.schema([("osm_type", pa.string()), ("osm_id", pa.int64()), ("tags", pa.string()), ("geometry", pa.binary()), ("bbox", bbox_t)],
                       metadata={b"geo": json.dumps(geo).encode()})
    tot = None
    with pyogrio.open_arrow(fgb, batch_size=row_group_size, return_fids=False, use_pyarrow=True) as (meta, reader):
        gcol = meta["geometry_name"] or "wkb_geometry"
        with pq.ParquetWriter(path, schema, compression="zstd") as w:
            for b in reader:
                wkb = b.column(gcol)
                bounds = shapely.bounds(shapely.from_wkb(wkb.to_numpy(zero_copy_only=False)))
                if len(bounds):
                    lo, hi = bounds[:, :2].min(axis=0), bounds[:, 2:].max(axis=0)
                    tot = [min(tot[0], lo[0]), min(tot[1], lo[1]), max(tot[2], hi[0]), max(tot[3], hi[1])] if tot else [lo[0], lo[1], hi[0], hi[1]]
                bb = pa.StructArray.from_arrays([pa.array(bounds[:, i]) for i in range(4)], fields=list(bbox_t))
                t = pa.table([b.column("osm_type"), b.column("osm_id").cast(pa.int64()), b.column("tags"), wkb.cast(pa.binary()), bb], schema=schema)
                w.write_table(t, row_group_size=row_group_size)
    return os.path.getsize(path), ([round(float(x), 5) for x in tot] if tot else None)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pbf")
    ap.add_argument("--region")
    ap.add_argument("--out")
    ap.add_argument("--parquet", action="store_true")
    ap.add_argument("--source-bytes", type=int, help="size of the extract before osmium tags-filter, for the report")
    ap.add_argument("--print-filter", action="store_true", help="print the osmium tags-filter expressions and stop")
    a = ap.parse_args(argv)
    if a.print_filter:
        print(" ".join(filter_expressions(load_spec())))
        return 0
    if not (a.pbf and a.region and a.out): ap.error("--pbf, --region and --out are needed")
    build(a.pbf, a.region, a.out, parquet=a.parquet, source_bytes=a.source_bytes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
