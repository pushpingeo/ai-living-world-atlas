"""Two separate axes, because they vary independently:

- coverage: how much of the world a layer spans (global ... local), from its extent
- detail:   how fine the data is, as an approximate ground resolution in metres

Detail is estimated from the strongest signal available, and we record which one was used:
  pixel-size   raster cell size reported by the service (direct)
  stated       a scale or resolution written by the publisher ("1:10,000", "25 m grid")
  tile-cache   the finest level the publisher cached tiles to
  display      the scale range the publisher set for drawing the layer (weakest; it's a styling choice)
Scale denominators become metres with the usual cartographic rule: resolution ~ denominator / 2000
(0.5 mm at map scale), so 1:50,000 ~ 25 m.
"""
from __future__ import annotations

import math
import re

# Detail levels are named by map scale, not by geography, so they can't be confused with coverage:
# a global layer can be 10 m, and a local one can be crude.
DETAIL_BANDS = [  # (upper bound in metres, label, description)
    (2.5, "1:5k", "site plans, 1:5,000 or larger"),
    (12.5, "1:25k", "street level, ~1:10,000-1:25,000"),
    (50, "1:100k", "~1:50,000-1:100,000"),
    (250, "1:500k", "~1:250,000-1:500,000"),
    (1000, "1:2M", "~1:1M-1:2M"),
    (float("inf"), "coarser", "smaller than 1:2M, or aggregated to large cells"),
]
COVERAGE_BANDS = [  # (upper bound in km2 of the WGS84 extent, label)
    (1_000, "local"),
    (50_000, "regional"),
    (1_500_000, "national"),
    (15_000_000, "continental"),
    (float("inf"), "global"),
]

_SCALE = re.compile(r"\b1\s*:\s*(\d{1,3}(?:[ ,.]?\d{3})+|\d+)\s*(k|m|000)?\b", re.I)
_K_SCALE = re.compile(r"\b(\d{1,4})\s*k\b(?!m)", re.I)  # "50k", "250K" (not "km")
_GRID = re.compile(r"\b(\d+(?:\.\d+)?)\s*(m|metres?|meters?|km|kilomet(?:re|er)s?)\s*(?:x\s*\d+(?:\.\d+)?\s*(?:m|km)\s*)?"
                   r"(?:resolution|grid|cells?|pixels?|raster|square|squares|hex)", re.I)
_GRID2 = re.compile(r"\b(?:resolution|grid|cell size|pixel size)\s*(?:of)?\s*(\d+(?:\.\d+)?)\s*(m|metres?|meters?|km)\b", re.I)


def stated_resolution_m(*texts: str) -> tuple[float | None, str]:
    """Look for a scale or ground resolution written by the publisher. Returns (metres, matched text)."""
    best, hit = None, ""
    for t in texts:
        if not t:
            continue
        for m in _SCALE.finditer(t):
            n = float(re.sub(r"[ ,.]", "", m.group(1)))
            suf = (m.group(2) or "").lower()
            n *= {"k": 1e3, "m": 1e6, "000": 1e3}.get(suf, 1)
            if 500 <= n <= 1e8:
                r = n / 2000
                if best is None or r < best:
                    best, hit = r, m.group(0)
        for m in _K_SCALE.finditer(t):
            n = float(m.group(1)) * 1000
            if 1000 <= n <= 1e7 and re.search(r"scale|os|map|vector|raster|data", t, re.I):
                r = n / 2000
                if best is None or r < best:
                    best, hit = r, m.group(0)
        for rx in (_GRID, _GRID2):
            for m in rx.finditer(t):
                v = float(m.group(1)) * (1000 if m.group(2).lower().startswith("k") else 1)
                if 0.05 <= v <= 100_000 and (best is None or v < best):
                    best, hit = v, m.group(0)
    return best, hit.strip()


def band(metres: float | None) -> tuple[str, str]:
    if metres is None:
        return "", ""
    for ub, label, scale in DETAIL_BANDS:
        if metres <= ub:
            return label, scale
    return "", ""


def extent_km2(bbox) -> float | None:
    if not bbox or len(bbox) != 4:
        return None
    x0, y0, x1, y1 = bbox
    r = 6371.0
    return abs(math.radians(x1 - x0) * (math.sin(math.radians(y1)) - math.sin(math.radians(y0)))) * r * r


def coverage_level(bbox) -> str:
    a = extent_km2(bbox)
    if a is None:
        return ""
    for ub, label in COVERAGE_BANDS:
        if a <= ub:
            return label
    return ""


def derive(row: dict) -> dict:
    """Best-estimate detail for a layer row, plus which signal it came from."""
    detail, src, evidence = None, "", ""
    if row.get("pixel_size_m"):
        detail, src, evidence = float(row["pixel_size_m"]), "pixel-size", f"{row['pixel_size_m']} m cells"
    if detail is None and row.get("stated_scale"):
        detail, src, evidence = row["stated_scale"] / 2000, "metadata", f"metadata says 1:{row['stated_scale']:,.0f}"
    if detail is None:
        m, hit = stated_resolution_m(row.get("title", ""), row.get("portal_title", ""), row.get("abstract", ""),
                                     row.get("portal_abstract", ""), row.get("service_abstract", ""))
        if m:
            detail, src, evidence = m, "stated", hit
    # Tile caches routinely go down to ~1:1,000 whatever the data, so only an early stop tells us anything.
    if detail is None and (row.get("cache_finest_scale") or 0) >= 20_000:
        detail, src, evidence = row["cache_finest_scale"] / 2000, "tile-cache", f"cached only to 1:{row['cache_finest_scale']:,.0f}"
    # A layer hidden until you zoom past 1:N was meant for close-up use. Visible-at-all-scales says nothing.
    if detail is None and row.get("scale_coarsest") and row["scale_coarsest"] <= 1_000_000:
        detail, src, evidence = row["scale_coarsest"] / 2000, "display", f"drawn only from 1:{row['scale_coarsest']:,.0f}"
    label, scale = band(detail)
    return {
        "detail_m": round(detail, 2) if detail else None, "detail_level": label, "detail_scale": scale,
        "detail_source": src, "detail_evidence": evidence[:80],
        "extent_km2": round(extent_km2(row.get("bbox")) or 0, 1) or None, "coverage_level": coverage_level(row.get("bbox")),
    }
