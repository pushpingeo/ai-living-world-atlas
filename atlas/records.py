"""Curated records from a seed file: download-only sources (files, cloud buckets, APIs, landing pages), and services
whose own metadata is too thin to pass but which we have checked by hand (vocab/seeds/values.yaml: rasters that return
a value at a point). The seed entry carries the metadata. An endpoint may give its own `capabilities`, `info`
(merged into the endpoint info, e.g. how to sample it), `service_url` and `check_url`; the check is a plain GET of
`check_url`, else of `url`."""
from __future__ import annotations

from datetime import datetime, timezone

from .endpoints import dumps
from .net import Client
from .record import Layer, to_wgs84

# geojson: a download-only dataset converted and hosted by the atlas (atlas/files.py); fetch_features filters it.
CAPS = {"download": ["download"], "cloud": ["download", "cloud"], "api": ["query"], "landing": [], "geojson": ["query", "download"],
        "opendap": ["download", "sample"]}
CHECK_URL: dict[str, str] = {}  # uid -> URL the check fetches; also marks a layer as a curated record (spike.py)


def to_layers(records: list[dict]) -> list[Layer]:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    out = []
    for s in records:
        ctx = s["_ctx"]
        for i, e in enumerate(s.get("endpoints") or []):
            b = s.get("bbox")
            L = Layer(
                layer_url=e["url"], service_url=e.get("service_url") or e["url"], service_type=e["protocol"], layer_name=f"{s['id']}:{i}",
                title=s["title"], abstract=s.get("abstract", ""), keywords=list(s.get("concepts_hint") or []),
                licence_text=s.get("licence", ""), landing_page=s.get("landing_page", ""),
                bbox=to_wgs84(*b) if b else None, geometry_type=s.get("geometry_type") or ("file" if e["protocol"] in ("download", "cloud") else ""),
                capabilities=list(e.get("capabilities") or CAPS.get(e["protocol"], [])), crawled_at=now,
                endpoint_info=dumps({"protocol": e["protocol"], "format": e.get("format", ""), **(e.get("info") or {})}),
                pixel_size_m=s.get("detail_m"), **ctx,
            )
            CHECK_URL[L.uid] = e.get("check_url") or e["url"]
            out.append(L)
    return out


async def check(c: Client, layer: Layer) -> tuple[str, str]:
    r = await c.get(CHECK_URL.get(layer.uid) or layer.layer_url, retries=1)
    if r.ok:
        return "ok", f"HTTP {r.status}"
    return "fail", r.error or f"HTTP {r.status}"
