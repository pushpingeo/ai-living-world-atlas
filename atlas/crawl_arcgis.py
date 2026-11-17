"""Walk an ArcGIS Server / ArcGIS Online services directory and emit Layer records."""
from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone

from . import endpoints
from .net import Client
from .record import Layer, clean_text, to_wgs84

KEEP_TYPES = {"MapServer", "FeatureServer", "ImageServer", "VectorTileServer"}
SKIP_LAYER_TYPES = {"Group Layer", "Annotation Layer", "Annotation SubLayer", "Table"}


def services_root(url: str) -> str | None:
    """Turn anything that looks like an ArcGIS REST URL into its .../rest/services root."""
    m = re.search(r"^(https?://[^?#]+?/rest/services)", url, flags=re.I)
    if m:
        return m.group(1)
    m = re.search(r"^(https?://[^?#]+?)/services/?(\?|$)", url, flags=re.I)  # .../arcgis/services (SOAP root)
    if m:
        return m.group(1) + "/rest/services"
    return None


def service_url_of(url: str) -> str | None:
    """https://host/.../rest/services/Folder/Name/MapServer/3 -> .../MapServer"""
    m = re.search(r"^(https?://[^?#]+?/rest/services/.+?/(MapServer|FeatureServer|ImageServer|VectorTileServer))", url, flags=re.I)
    return m.group(1) if m else None


def _txt(v) -> str:
    return clean_text(v)  # descriptions are often HTML


def _bbox(extent) -> list[float] | None:
    if not isinstance(extent, dict):
        return None
    sr = extent.get("spatialReference") or {}
    wkid = sr.get("latestWkid") or sr.get("wkid")
    return to_wgs84(extent.get("xmin"), extent.get("ymin"), extent.get("xmax"), extent.get("ymax"), wkid=wkid, wkt=sr.get("wkt"))


async def list_services(c: Client, root: str, max_services: int = 1500) -> tuple[list[str], dict]:
    """Return service URLs under a services root (recursing folders)."""
    out: list[str] = []
    info = {"root": root, "status": None, "error": ""}
    queue = [root]
    seen = set()
    while queue and len(out) < max_services:
        url = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)
        r = await c.get(url + "?f=json")
        if url == root:
            info["status"] = r.status
            info["ms"] = r.ms
        if not r.ok:
            info["error"] = info["error"] or r.error or f"HTTP {r.status}"
            continue
        try:
            j = r.json()
        except Exception:
            info["error"] = info["error"] or "not json"
            continue
        if "error" in j:
            info["error"] = info["error"] or str(j["error"])[:200]
            continue
        for f in j.get("folders") or []:
            queue.append(f"{root}/{f}")
        for s in j.get("services") or []:
            if s.get("type") in KEEP_TYPES:
                name = s["name"]  # includes folder prefix
                out.append(f"{root}/{name}/{s['type']}")
    return out[:max_services], info


async def crawl_service(c: Client, surl: str, ctx: dict) -> tuple[list[Layer], dict]:
    stype = surl.rsplit("/", 1)[-1]
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    status = {"service_url": surl, "service_type": f"arcgis-{stype.lower()}", "ok": False, "ms": 0, "error": "", "n_layers": 0}
    r = await c.get(surl + "?f=json")
    status["ms"] = r.ms
    if not r.ok:
        status["error"] = r.error or f"HTTP {r.status}"
        return [], status
    try:
        sj = r.json()
    except Exception:
        status["error"] = "not json"
        return [], status
    if "error" in sj:
        status["error"] = str(sj["error"])[:200]
        return [], status
    status["ok"] = True

    doc = sj.get("documentInfo") or {}
    svc_title = _txt(doc.get("Title")) or _txt(sj.get("name")) or surl.rsplit("/", 2)[-2]
    svc_abs = _txt(sj.get("serviceDescription")) or _txt(sj.get("description"))
    svc_lic = _txt(sj.get("copyrightText"))
    svc_kw = [k.strip() for k in re.split(r"[,;]", doc.get("Keywords") or "") if k.strip()]
    lods = ((sj.get("tileInfo") or {}).get("lods") or [])
    cache_finest = min((l.get("scale") for l in lods if l.get("scale")), default=None)
    px = None
    if stype == "ImageServer" and sj.get("pixelSizeX"):
        px = float(sj["pixelSizeX"])
        sr = (sj.get("spatialReference") or sj.get("extent", {}).get("spatialReference") or {})
        if (sr.get("latestWkid") or sr.get("wkid")) in (4326, 4258, 4269):
            ext = _bbox(sj.get("extent")) or [0, 0, 0, 0]
            import math
            px = px * 111_320 * math.cos(math.radians((ext[1] + ext[3]) / 2))
    base = dict(
        cors=r.cors,
        cache_finest_scale=cache_finest,
        service_url=surl, service_type=status["service_type"], service_title=svc_title,
        service_abstract=svc_abs, crawled_at=now, service_ms=r.ms, **ctx,
    )

    layers: list[Layer] = []
    if stype in ("ImageServer", "VectorTileServer"):
        caps, info = endpoints.arcgis(stype, sj)
        layers.append(Layer(
            capabilities=caps, endpoint_info=endpoints.dumps(info),
            layer_url=surl, layer_name="0", title=svc_title, abstract=svc_abs, keywords=svc_kw,
            licence_text=svc_lic, bbox=_bbox(sj.get("fullExtent") or sj.get("extent") or sj.get("initialExtent")),
            geometry_type="raster" if stype == "ImageServer" else "vector-tiles",
            has_time=bool(sj.get("timeInfo")), pixel_size_m=round(px, 3) if px else None,
            scale_finest=(sj.get("maxScale") or None), scale_coarsest=(sj.get("minScale") or None), **base,
        ))
    else:
        lr = await c.get(surl + "/layers?f=json")
        items = []
        if lr.ok:
            try:
                lj = lr.json()
                items = lj.get("layers") or []
            except Exception:
                items = []
        if not items:  # fall back to the summary list in the service JSON
            items = [dict(x, type=x.get("type", "Feature Layer")) for x in (sj.get("layers") or []) if not x.get("subLayerIds")]
        for L in items:
            if L.get("type") in SKIP_LAYER_TYPES or L.get("subLayerIds"):
                continue
            flds = [f"{f.get('name')}|{f.get('alias') or ''}|{(f.get('type') or '').replace('esriFieldType', '')}" for f in (L.get("fields") or [])][:200]
            gt = (L.get("geometryType") or "").replace("esriGeometry", "").lower() or ("raster" if L.get("type") == "Raster Layer" else "")
            caps, info = endpoints.arcgis(stype, sj, L)
            layers.append(Layer(
                capabilities=caps, endpoint_info=endpoints.dumps(info),
                layer_url=f"{surl}/{L.get('id')}", layer_name=str(L.get("id")), title=_txt(L.get("name")),
                abstract=_txt(L.get("description")), keywords=svc_kw,
                licence_text=_txt(L.get("copyrightText")) or svc_lic,
                bbox=_bbox(L.get("extent")) or _bbox(sj.get("fullExtent") or sj.get("initialExtent")),
                geometry_type=gt, fields=flds, has_time=bool(L.get("timeInfo")),
                # ArcGIS: minScale is the coarsest scale shown, maxScale the finest; 0 means no limit
                scale_finest=(L.get("maxScale") or None), scale_coarsest=(L.get("minScale") or None),
                native_crs=str(((L.get("extent") or {}).get("spatialReference") or {}).get("latestWkid") or ((L.get("extent") or {}).get("spatialReference") or {}).get("wkid") or ""),
                **base,
            ))
    status["n_layers"] = len(layers)
    return layers, status


async def check_layer(c: Client, layer: Layer) -> tuple[str, str]:
    """Tiny 'does it return data' check. Returns (status, detail)."""
    query_refused = False
    if layer.service_type in ("arcgis-featureserver", "arcgis-mapserver") and layer.geometry_type not in ("raster", ""):
        r = await c.get(layer.layer_url + "/query?where=1%3D1&returnCountOnly=true&f=json", retries=0)
        j = {}
        if r.ok:
            try:
                j = r.json()
            except Exception:
                j = {}
        if "count" in j:
            return ("ok" if j["count"] > 0 else "empty"), f"count={j['count']}"
        if layer.service_type == "arcgis-featureserver":
            return "fail", r.error or (f"HTTP {r.status}" if not r.ok else str(j.get("error", "no count"))[:120])
        query_refused = True  # some servers advertise Query and refuse it; the sweep drops the capability
        # MapServers (especially cached tile services) often refuse query: try an image instead
    if layer.service_type in ("arcgis-imageserver", "arcgis-mapserver") or layer.geometry_type == "raster":
        if not layer.bbox:
            return "unchecked", "no bbox"
        x0, y0, x1, y1 = layer.bbox
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        dx, dy = (x1 - x0) / 20, (y1 - y0) / 20
        target = layer.service_url if layer.service_type == "arcgis-imageserver" else layer.service_url
        op = "exportImage" if layer.service_type == "arcgis-imageserver" else "export"
        extra = "" if op == "exportImage" else f"&layers=show:{layer.layer_name}"
        r = await c.get(f"{target}/{op}?bbox={cx-dx},{cy-dy},{cx+dx},{cy+dy}&bboxSR=4326&size=64,64&format=png&f=image{extra}", retries=0)
        if r.ok and "image" in r.content_type:
            return "ok", "image; query refused" if query_refused else "image"
        if layer.service_type == "arcgis-mapserver":
            # cache-only (tile) services: ask for one Web Mercator tile at the layer's centre
            import math

            z = max(0, min(16, int(math.log2(360 / max(x1 - x0, 1e-6)))))
            n = 2 ** z
            tx = int((cx + 180) / 360 * n)
            lat = math.radians(max(min(cy, 85), -85))
            ty = int((1 - math.log(math.tan(lat) + 1 / math.cos(lat)) / math.pi) / 2 * n)
            t = await c.get(f"{layer.service_url}/tile/{z}/{ty}/{tx}", retries=0)
            if t.ok and "image" in t.content_type:
                return "ok", f"tile z{z}" + ("; query refused" if query_refused else "")
            if t.status in (404, 400):
                return "unchecked", "tile cache; sample tile missing"
        return "fail", r.error or f"HTTP {r.status} {r.content_type[:30]}"
    return "unchecked", "type not checked"
