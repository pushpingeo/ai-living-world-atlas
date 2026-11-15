"""Parse OGC WMS and WFS GetCapabilities into Layer records."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from defusedxml import ElementTree as ET

from .net import Client
from .record import Layer, clean_text, to_wgs84


def base_url(u: str) -> str:
    """Strip the OGC request parameters but keep any vendor params (e.g. map=...)."""
    p = urlsplit(u)
    drop = {"service", "request", "version", "acceptversions", "tiled"}
    q = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if k.lower() not in drop]
    return urlunsplit((p.scheme, p.netloc, p.path, urlencode(q), ""))


def caps_url(base: str, service: str) -> str:
    sep = "&" if "?" in base else "?"
    version = "1.3.0" if service == "WMS" else "2.0.0"
    return f"{base}{sep}service={service}&request=GetCapabilities&version={version}"


def _strip(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _child(el, name):
    for c in el:
        if _strip(c.tag) == name:
            return c
    return None


def _children(el, name):
    return [c for c in el if _strip(c.tag) == name]


def _text(el, name) -> str:
    c = _child(el, name) if el is not None else None
    return clean_text(c.text) if c is not None and c.text else ""


def _keywords(el) -> list[str]:
    out = []
    for kl in _children(el, "KeywordList") + _children(el, "Keywords"):
        for k in kl:
            if k.text and k.text.strip():
                out.append(k.text.strip())
        if kl.text and kl.text.strip() and not len(kl):  # WFS 1.0 comma list
            out += [x.strip() for x in kl.text.split(",") if x.strip()]
    return out[:50]


def _service_block(root):
    svc = _child(root, "Service")
    if svc is None:
        svc = _child(root, "ServiceIdentification")
    if svc is None:
        return "", "", ""
    title = _text(svc, "Title")
    abstract = _text(svc, "Abstract")
    lic = " | ".join(x for x in (_text(svc, "Fees"), _text(svc, "AccessConstraints")) if x and x.lower() not in ("none", "no", "unknown"))
    return title, abstract, lic


def _publisher(root) -> str:
    for path in (("Service", "ContactInformation", "ContactPersonPrimary", "ContactOrganization"),
                 ("ServiceProvider", "ProviderName")):
        el = root
        for p in path:
            el = _child(el, p) if el is not None else None
        if el is not None and el.text and el.text.strip():
            return el.text.strip()
    return ""


def parse_wms(xml: bytes, base: str, ctx: dict, ms: int) -> tuple[list[Layer], dict]:
    root = ET.fromstring(xml)
    if _strip(root.tag) in ("ServiceExceptionReport", "ExceptionReport"):
        raise ValueError("exception report")
    s_title, s_abs, s_lic = _service_block(root)
    cap = _child(root, "Capability")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    out: list[Layer] = []

    def walk(el, inherited_bbox, inherited_crs, parent_title):
        name = _text(el, "Name")
        title = _text(el, "Title")
        bbox = inherited_bbox
        g = _child(el, "EX_GeographicBoundingBox")
        if g is not None:
            bbox = to_wgs84(_text(g, "westBoundLongitude"), _text(g, "southBoundLatitude"), _text(g, "eastBoundLongitude"), _text(g, "northBoundLatitude"))
        else:
            ll = _child(el, "LatLonBoundingBox")
            if ll is not None:
                bbox = to_wgs84(ll.get("minx"), ll.get("miny"), ll.get("maxx"), ll.get("maxy"))
        crs = [c.text.strip() for c in _children(el, "CRS") + _children(el, "SRS") if c.text] or inherited_crs
        md = _child(el, "MetadataURL")
        md_url = ""
        if md is not None:
            orr = _child(md, "OnlineResource")
            if orr is not None:
                md_url = next((v for k, v in orr.attrib.items() if k.endswith("href")), "")
        kids = _children(el, "Layer")
        if name:
            out.append(Layer(
                layer_url=f"{base}#{name}", service_url=base, service_type="wms", layer_name=name,
                title=title, abstract=_text(el, "Abstract"), keywords=_keywords(el),
                service_title=s_title, service_abstract=s_abs, licence_text=s_lic,
                bbox=bbox, native_crs=",".join(crs[:5]), metadata_url=md_url,
                has_time=any((d.get("name") or "").lower() == "time" for d in _children(el, "Dimension")),
                geometry_type="map-image", crawled_at=now, service_ms=ms,
                **ctx,
            ))
        for k in kids:
            walk(k, bbox, crs, title or parent_title)

    if cap is not None:
        for top in _children(cap, "Layer"):
            walk(top, None, [], "")
    pub = _publisher(root)
    if pub:
        for L in out:
            L.publisher = L.publisher or pub
    return out, {"service_title": s_title}


def parse_wfs(xml: bytes, base: str, ctx: dict, ms: int) -> tuple[list[Layer], dict]:
    root = ET.fromstring(xml)
    if _strip(root.tag) in ("ServiceExceptionReport", "ExceptionReport"):
        raise ValueError("exception report")
    s_title, s_abs, s_lic = _service_block(root)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    out: list[Layer] = []
    ftl = _child(root, "FeatureTypeList")
    for ft in _children(ftl, "FeatureType") if ftl is not None else []:
        name = _text(ft, "Name")
        if not name:
            continue
        bbox = None
        w = _child(ft, "WGS84BoundingBox")
        if w is not None:
            lc, uc = _text(w, "LowerCorner").split(), _text(w, "UpperCorner").split()
            if len(lc) == 2 and len(uc) == 2:
                bbox = to_wgs84(lc[0], lc[1], uc[0], uc[1])
        else:
            ll = _child(ft, "LatLongBoundingBox")
            if ll is not None:
                bbox = to_wgs84(ll.get("minx"), ll.get("miny"), ll.get("maxx"), ll.get("maxy"))
        crs = _text(ft, "DefaultCRS") or _text(ft, "DefaultSRS") or _text(ft, "SRS")
        md = _child(ft, "MetadataURL")
        md_url = ""
        if md is not None:
            md_url = (md.text or "").strip() or next((v for k, v in md.attrib.items() if k.endswith("href")), "")
        out.append(Layer(
            layer_url=f"{base}#{name}", service_url=base, service_type="wfs", layer_name=name,
            title=_text(ft, "Title"), abstract=_text(ft, "Abstract"), keywords=_keywords(ft),
            service_title=s_title, service_abstract=s_abs, licence_text=s_lic, bbox=bbox,
            native_crs=crs, metadata_url=md_url, geometry_type="features", crawled_at=now,
            service_ms=ms, **ctx,
        ))
    pub = _publisher(root)
    if pub:
        for L in out:
            L.publisher = L.publisher or pub
    return out, {"service_title": s_title}


async def crawl_ogc(c: Client, base: str, service: str, ctx: dict, max_layers: int = 3000) -> tuple[list[Layer], dict]:
    status = {"service_url": base, "service_type": service.lower(), "ok": False, "ms": 0, "error": "", "n_layers": 0}
    r = await c.get(caps_url(base, service))
    status["ms"] = r.ms
    if not r.ok:
        status["error"] = r.error or f"HTTP {r.status}"
        return [], status
    try:
        fn = parse_wms if service == "WMS" else parse_wfs
        layers, _ = fn(r.body, base, ctx, r.ms)
    except Exception as e:
        status["error"] = f"parse: {type(e).__name__}: {e}"[:200]
        return [], status
    status["ok"] = True
    status["n_layers"] = len(layers)
    return layers[:max_layers], status


async def check_layer(c: Client, layer: Layer) -> tuple[str, str]:
    if not layer.bbox:
        return "unchecked", "no bbox"
    x0, y0, x1, y1 = layer.bbox
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    dx, dy = max((x1 - x0) / 10, 1e-4), max((y1 - y0) / 10, 1e-4)
    b = layer.service_url
    sep = "&" if "?" in b else "?"
    if layer.service_type == "wms":
        url = (f"{b}{sep}service=WMS&request=GetMap&version=1.1.1&layers={layer.layer_name}&styles="
               f"&srs=EPSG:4326&bbox={cx-dx},{cy-dy},{cx+dx},{cy+dy}&width=64&height=64&format=image/png&transparent=true")
        r = await c.get(url, retries=0)
        if r.ok and "image" in r.content_type:
            return "ok", "image"
        return "fail", r.error or f"HTTP {r.status} {r.content_type[:30]}"
    url = f"{b}{sep}service=WFS&request=GetFeature&version=1.1.0&typeName={layer.layer_name}&maxFeatures=1"
    r = await c.get(url, retries=0)
    if r.ok and b"Exception" not in r.body[:2000]:
        return "ok", "feature"
    return "fail", r.error or f"HTTP {r.status}"
