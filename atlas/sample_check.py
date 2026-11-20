"""Read a value at a point through an endpoint's `sample` description, the way an agent would.
Used by the mcp-check workflow to test every sampled endpoint end to end. Needs pyproj and rasterio for the methods
that work in a national grid or read GeoTIFFs; the rest is the standard library.
"""
from __future__ import annotations

import json
import math
import urllib.request

UA = {"User-Agent": "ai-living-world-atlas probe (+https://github.com/pushpingeo/ai-living-world-atlas)"}


def _get(url: str, timeout: int = 60) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.read()


def to_crs(crs: str, lon: float, lat: float) -> tuple[float, float]:
    if not crs or crs.upper() in ("EPSG:4326", "CRS:84"):
        return lon, lat
    from pyproj import Transformer
    return Transformer.from_crs("EPSG:4326", crs, always_xy=True).transform(lon, lat)


def osgb_1km(e: float, n: float) -> str:
    """Ordnance Survey 1 km grid reference, e.g. NG2205."""
    e100, n100 = int(e // 100000), int(n // 100000)
    l1 = (19 - n100) - (19 - n100) % 5 + (e100 + 10) // 5
    l2 = (19 - n100) * 5 % 25 + e100 % 5
    letters = "ABCDEFGHJKLMNOPQRSTUVWXYZ"  # no I
    return f"{letters[l1]}{letters[l2]}{int(e % 100000) // 1000:02d}{int(n % 100000) // 1000:02d}"


def fill(t: str, smp: dict, lon: float, lat: float) -> str:
    d = smp.get("box_deg") or 0.001
    x, y = to_crs(smp.get("crs") or "", lon, lat)
    h = smp.get("box_m") or 2
    la, lo = math.floor(lat), math.floor(lon)
    vals = {"lon": lon, "lat": lat, "west": lon - d, "south": lat - d, "east": lon + d, "north": lat + d,
            "x": x, "y": y, "xmin": x - h, "ymin": y - h, "xmax": x + h, "ymax": y + h,
            "NS": "N" if la >= 0 else "S", "LAT": f"{abs(la):02d}", "EW": "E" if lo >= 0 else "W", "LON": f"{abs(lo):03d}"}
    if "{osgb_1km}" in t:
        vals["osgb_1km"] = osgb_1km(x, y)
    for k, v in vals.items():
        t = t.replace("{" + k + "}", f"{v:.6f}" if isinstance(v, float) else str(v))
    return t


def pointer(doc, path: str):
    for part in [p for p in path.split("/") if p != ""]:
        doc = doc[int(part)] if isinstance(doc, list) else doc[part]
    return doc


def raster_value(src_bytes_or_url, lon, lat, crs: str = ""):
    import rasterio
    from rasterio.io import MemoryFile
    from rasterio.warp import transform as wtransform

    def at(ds):
        xs, ys = wtransform("EPSG:4326", ds.crs, [lon], [lat]) if ds.crs else ([lon], [lat])
        v = next(ds.sample([(xs[0], ys[0])]))[0]
        return None if ds.nodata is not None and v == ds.nodata else float(v)

    if isinstance(src_bytes_or_url, (bytes, bytearray)):
        with MemoryFile(bytes(src_bytes_or_url)) as m, m.open() as ds:
            return at(ds)
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"), rasterio.open(src_bytes_or_url) as ds:
        return at(ds)


def read_value(ep: dict, lon: float, lat: float):
    """ep: one endpoint from get_dataset. Returns the value or an error string."""
    smp = (ep.get("details") or {}).get("sample") or {}
    use = ep.get("use") or {}
    m = smp.get("method")
    try:
        if m == "lerc-tile":
            import lerc
            ox, oy = smp["origin"]
            px, py = (lon - ox) / smp["cell_deg"], (oy - lat) / smp["cell_deg"]
            ts = smp.get("tile_size", 256)
            url = use["tile_url"].replace("{row}", str(int(py // ts))).replace("{col}", str(int(px // ts)))
            arr = lerc.decode(_get(url))[1]
            return float(arr[int(py) % ts, int(px) % ts])
        if m == "cog":
            url = fill(use.get("file_url") or "", smp, lon, lat)
            return raster_value("/vsicurl/" + url, lon, lat)
        if not use.get("sample_url"):
            return f"no sample_url ({m})"
        url = fill(use["sample_url"], smp, lon, lat)
        body = _get(url)
        if m == "wcs":
            return raster_value(body, lon, lat)
        if m == "opendap":
            import re
            g = re.search(rb"\[0\], (-?[\d.]+)", body)
            return float(g.group(1)) if g else body[:80]
        doc = json.loads(body)
        if smp.get("value_path"):
            return pointer(doc, smp["value_path"])
        if m == "identify":
            return doc.get("value")
        if m == "feature-info":
            f = doc.get("features") or [{}]
            return (f[0].get("properties") or {}).get(smp.get("field")) if f else "no feature"
        return str(doc)[:80]
    except Exception as e:  # report, don't stop the check
        return f"{type(e).__name__}: {e}"[:120]
