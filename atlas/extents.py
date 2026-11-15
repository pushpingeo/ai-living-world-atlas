"""False extents: find declared extents that look wrong, and measure the real one where we can.

An extent is suspect when:
  shared-default  it is identical for every layer of a service with 3+ layers (copied from the service)
  world           it spans more than 350 degrees of longitude
  grid-default    it is the whole British National Grid or similar CRS-wide box
  too-big-local   a local council layer claims a national or larger extent
ArcGIS feature and map layers can then report their true extent with one request
(query?returnExtentOnly=true). Other protocols stay flagged until we have a way to measure them.
"""
from __future__ import annotations

import asyncio
from collections import defaultdict

from .crawl_arcgis import _bbox
from .net import Client
from .resolution import coverage_level

GRID_DEFAULTS = [(-10, -7.5, 49.0, 50.2, 60.5, 62.0)]  # whole-GB grid as seen in WGS84: x0 range, y0 range, y1 range


def flag(layers) -> None:
    by_svc = defaultdict(list)
    for L in layers:
        by_svc[L.service_url].append(L)
    for svc, ls in by_svc.items():
        boxes = {tuple(round(v, 3) for v in L.bbox) for L in ls if L.bbox}
        shared = len(ls) >= 3 and len(boxes) == 1
        for L in ls:
            if not L.bbox:
                continue
            x0, y0, x1, y1 = L.bbox
            f = []
            if shared:
                f.append("shared-default")
            if x1 - x0 > 350:
                f.append("world")
            if any(a <= x0 <= b and c <= y0 <= d and e <= y1 <= g for a, b, c, d, e, g in GRID_DEFAULTS):
                f.append("grid-default")
            if L.publisher_type == "local-gov" and coverage_level(L.bbox) in ("national", "continental", "global"):
                f.append("too-big-local")
            L.extent_flags = f


async def measure(c: Client, layers, limit: int, deadline_ok) -> dict:
    """Ask ArcGIS for the true extent of suspect queryable layers. Returns counts for the report."""
    todo = [L for L in layers if L.extent_flags and L.service_type in ("arcgis-featureserver", "arcgis-mapserver")
            and "query" in (L.capabilities or [])][:limit]
    stats = {"suspect": sum(1 for L in layers if L.extent_flags), "attempted": len(todo), "measured": 0, "shrunk": 0, "empty": 0}

    async def one(L):
        if not deadline_ok():
            return
        r = await c.get(L.layer_url + "/query?where=1%3D1&returnExtentOnly=true&outSR=4326&f=json", retries=0)
        if not r.ok:
            return
        try:
            j = r.json()
        except Exception:
            return
        if j.get("count") == 0:
            stats["empty"] += 1
            return
        b = _bbox(j.get("extent"))
        if not b:
            return
        stats["measured"] += 1
        old = L.bbox
        L.declared_bbox, L.bbox, L.extent_source = old, b, "measured"
        if old and (b[2] - b[0]) * (b[3] - b[1]) < 0.5 * (old[2] - old[0]) * (old[3] - old[1]):
            stats["shrunk"] += 1

    await asyncio.gather(*[one(L) for L in todo])
    return stats
