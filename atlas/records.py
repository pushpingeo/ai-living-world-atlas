"""Download-only sources from a curated seed file: files, cloud buckets, APIs and landing pages.
There is no service to read metadata from, so the seed entry carries it, and the check is a plain GET."""
from __future__ import annotations

from datetime import datetime, timezone

from .endpoints import dumps
from .net import Client
from .record import Layer, to_wgs84

# geojson: a download-only dataset converted and hosted by the atlas (atlas/files.py); fetch_features filters it.
CAPS = {"download": ["download"], "cloud": ["download", "cloud"], "api": ["query"], "landing": [], "geojson": ["query", "download"]}


def to_layers(records: list[dict]) -> list[Layer]:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    out = []
    for s in records:
        ctx = s["_ctx"]
        for i, e in enumerate(s.get("endpoints") or []):
            b = s.get("bbox")
            out.append(Layer(
                layer_url=e["url"], service_url=e["url"], service_type=e["protocol"], layer_name=f"{s['id']}:{i}",
                title=s["title"], abstract=s.get("abstract", ""), keywords=list(s.get("concepts_hint") or []),
                licence_text=s.get("licence", ""), landing_page=s.get("landing_page", ""),
                bbox=to_wgs84(*b) if b else None, geometry_type=s.get("geometry_type") or ("file" if e["protocol"] in ("download", "cloud") else ""),
                capabilities=CAPS.get(e["protocol"], []), crawled_at=now,
                endpoint_info=dumps({"protocol": e["protocol"], "format": e.get("format", "")}),
                pixel_size_m=s.get("detail_m"), **ctx,
            ))
    return out


async def check(c: Client, layer: Layer) -> tuple[str, str]:
    r = await c.get(layer.layer_url, retries=1)
    if r.ok:
        return "ok", f"HTTP {r.status}"
    return "fail", r.error or f"HTTP {r.status}"
