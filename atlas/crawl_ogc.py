"""Parse OGC WMS, WFS, WMTS and WCS GetCapabilities into Layer records."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from defusedxml import ElementTree as ET

from . import endpoints
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
    version = {"WMS": "1.3.0", "WFS": "2.0.0", "WMTS": "1.0.0", "WCS": "2.0.1"}[service]
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


def _all(el, name):
    """All descendants with this local name."""
    return [e for e in el.iter() if _strip(e.tag) == name]


def _op_formats(root, op: str, param: str = "outputFormat") -> list[str]:
    """Formats from WMS Request/<op>/Format or OWS OperationsMetadata parameters."""
    out = []
    for e in _all(root, op):
        out += [f.text.strip() for f in _children(e, "Format") if f.text]
    for o in _all(root, "Operation"):
        if o.get("name") == op:
            for prm in _all(o, "Parameter"):
                if (prm.get("name") or "").lower() == param.lower():
                    out += [v.text.strip() for v in _all(prm, "Value") if v.text]
    return list(dict.fromkeys(out))[:20]


def _op_url(root, op: str) -> str:
    """The HTTP GET address a server gives for an operation (WMS Request/<op>/DCPType, or OWS OperationsMetadata).
    Proxies such as Mapbender's wms.php answer GetCapabilities at one address and GetMap at another."""
    els = list(_all(root, op)) + [o for o in _all(root, "Operation") if o.get("name") == op]
    for e in els:
        for g in _all(e, "Get"):
            href = next((v for k, v in g.attrib.items() if k.endswith("href")), "")
            if not href:
                orr = _child(g, "OnlineResource")
                href = next((v for k, v in (orr.attrib if orr is not None else {}).items() if k.endswith("href")), "")
            if href.strip():
                return href.strip()
    return ""


def _constraint(root, name: str) -> str:
    for c in _all(root, "Constraint"):
        if c.get("name") == name:
            v = _all(c, "DefaultValue")
            return (v[0].text or "").strip() if v else ""
    return ""


def parse_wms(xml: bytes, base: str, ctx: dict, ms: int) -> tuple[list[Layer], dict]:
    root = ET.fromstring(xml)
    if _strip(root.tag) in ("ServiceExceptionReport", "ExceptionReport"):
        raise ValueError("exception report")
    s_title, s_abs, s_lic = _service_block(root)
    cap = _child(root, "Capability")
    getmap_formats = _op_formats(root, "GetMap")
    getmap_url = _op_url(root, "GetMap")
    has_gfi = bool(_all(root, "GetFeatureInfo"))
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    out: list[Layer] = []

    def walk(el, inherited_bbox, inherited_crs, parent_title, inh_scale=(None, None)):
        name = _text(el, "Name")
        fin, coa = inh_scale
        try:
            if _text(el, "MinScaleDenominator"):
                fin = float(_text(el, "MinScaleDenominator"))
            if _text(el, "MaxScaleDenominator"):
                coa = float(_text(el, "MaxScaleDenominator"))
            sh = _child(el, "ScaleHint")  # WMS 1.1.1: ground size of a pixel diagonal, in metres
            if sh is not None:
                k = 0.00028 * 2 ** 0.5
                fin = float(sh.get("min")) / k if float(sh.get("min") or 0) > 0 else fin
                coa = float(sh.get("max")) / k if float(sh.get("max") or 0) > 0 else coa
        except (TypeError, ValueError):
            pass
        if coa and coa > 1e12:
            coa = None  # "infinity" in practice
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
                capabilities=["render"] + (["feature-info"] if has_gfi and el.get("queryable") in ("1", "true") else [])
                + (["time"] if any((d.get("name") or "").lower() == "time" for d in _children(el, "Dimension")) else []),
                endpoint_info=endpoints.dumps({"protocol": "wms", "version": root.get("version"), "image_formats": getmap_formats[:8],
                                               "crs": crs[:8], "opaque": el.get("opaque") in ("1", "true"),
                                               **({"get_url": getmap_url} if getmap_url else {})}),
                scale_finest=fin, scale_coarsest=coa,
                **ctx,
            ))
        for k in kids:
            walk(k, bbox, crs, title or parent_title, (fin, coa))

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
    wfs_formats = _op_formats(root, "GetFeature")
    getfeature_url = _op_url(root, "GetFeature")
    paging = _constraint(root, "ImplementsResultPaging").upper() == "TRUE"
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
            capabilities=["query", "download"],
            endpoint_info=endpoints.dumps({"protocol": "wfs", "version": root.get("version"), "paging": paging,
                                           "output_formats": ([f.text.strip() for f in _all(ft, "Format") if f.text] or wfs_formats)[:12],
                                           **({"get_url": getfeature_url} if getfeature_url else {})}),
            service_ms=ms, **ctx,
        ))
    pub = _publisher(root)
    if pub:
        for L in out:
            L.publisher = L.publisher or pub
    return out, {"service_title": s_title}


def _ows_bbox(el):
    w = _child(el, "WGS84BoundingBox")
    if w is None:
        return None
    lc, uc = _text(w, "LowerCorner").split(), _text(w, "UpperCorner").split()
    if len(lc) == 2 and len(uc) == 2:
        return to_wgs84(lc[0], lc[1], uc[0], uc[1])
    return None


def parse_wmts(xml: bytes, base: str, ctx: dict, ms: int) -> tuple[list[Layer], dict]:
    root = ET.fromstring(xml)
    if _strip(root.tag) in ("ServiceExceptionReport", "ExceptionReport"):
        raise ValueError("exception report")
    s_title, s_abs, s_lic = _service_block(root)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    contents = _child(root, "Contents")
    if contents is None:
        return [], {}
    sets = {}
    for tms in _children(contents, "TileMatrixSet"):
        ident = _text(tms, "Identifier")
        scales = []
        for tm in _children(tms, "TileMatrix"):
            try:
                scales.append(float(_text(tm, "ScaleDenominator")))
            except ValueError:
                pass
        crs = _text(tms, "SupportedCRS")
        wk = _text(tms, "WellKnownScaleSet")
        sets[ident] = {"crs": crs, "levels": len(scales), "finest": min(scales) if scales else None,
                       "web_mercator": bool(re.search(r"3857|900913|GoogleMapsCompatible", crs + wk + ident, re.I))}
    out = []
    for el in _children(contents, "Layer"):
        ident = _text(el, "Identifier")
        if not ident:
            continue
        links = [_text(l, "TileMatrixSet") for l in _children(el, "TileMatrixSetLink")]
        used = [sets[k] for k in links if k in sets]
        finest = min((u["finest"] for u in used if u["finest"]), default=None)
        templates = [r.get("template") for r in _children(el, "ResourceURL") if r.get("resourceType") == "tile"]
        out.append(Layer(
            layer_url=f"{base}#{ident}", service_url=base, service_type="wmts", layer_name=ident,
            title=_text(el, "Title"), abstract=_text(el, "Abstract"), keywords=_keywords(el),
            service_title=s_title, service_abstract=s_abs, licence_text=s_lic, bbox=_ows_bbox(el),
            geometry_type="tiles", crawled_at=now, service_ms=ms, cache_finest_scale=finest,
            capabilities=["tiles"],
            endpoint_info=endpoints.dumps({
                "protocol": "wmts", "tile_matrix_sets": links[:6], "formats": [f.text for f in _children(el, "Format") if f.text][:6],
                "web_mercator_standard": any(u["web_mercator"] for u in used), "zoom_levels": max((u["levels"] for u in used), default=None),
                "tile_template": templates[0] if templates else None,
            }),
            **ctx,
        ))
    pub = _publisher(root)
    for L in out:
        L.publisher = L.publisher or pub
    return out, {"service_title": s_title}


def parse_wcs(xml: bytes, base: str, ctx: dict, ms: int) -> tuple[list[Layer], dict]:
    root = ET.fromstring(xml)
    if _strip(root.tag) in ("ServiceExceptionReport", "ExceptionReport"):
        raise ValueError("exception report")
    s_title, s_abs, s_lic = _service_block(root)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    formats = [f.text.strip() for f in _all(root, "formatSupported") if f.text][:10]
    out = []
    for el in _all(root, "CoverageSummary") + _all(root, "CoverageOfferingBrief"):
        ident = _text(el, "CoverageId") or _text(el, "Identifier") or _text(el, "name")
        if not ident:
            continue
        bbox = _ows_bbox(el)
        env = _child(el, "lonLatEnvelope")
        if bbox is None and env is not None:
            pos = [p.text.split() for p in _children(env, "pos") if p.text]
            if len(pos) == 2:
                bbox = to_wgs84(pos[0][0], pos[0][1], pos[1][0], pos[1][1])
        out.append(Layer(
            layer_url=f"{base}#{ident}", service_url=base, service_type="wcs", layer_name=ident,
            title=_text(el, "Title") or _text(el, "label") or ident, abstract=_text(el, "Abstract") or _text(el, "description"),
            keywords=_keywords(el), service_title=s_title, service_abstract=s_abs, licence_text=s_lic, bbox=bbox,
            geometry_type="raster", crawled_at=now, service_ms=ms, capabilities=["download", "pixels"],
            endpoint_info=endpoints.dumps({"protocol": "wcs", "version": root.get("version"), "formats": formats}),
            **ctx,
        ))
    pub = _publisher(root)
    for L in out:
        L.publisher = L.publisher or pub
    return out, {"service_title": s_title}


async def crawl_ogc(c: Client, base: str, service: str, ctx: dict, max_layers: int = 3000) -> tuple[list[Layer], dict]:
    ctx = dict(ctx)
    curated_licence = ctx.pop("curated_licence", "")
    status = {"service_url": base, "service_type": service.lower(), "ok": False, "ms": 0, "error": "", "n_layers": 0}
    r = await c.get(caps_url(base, service))
    status["ms"] = r.ms
    if not r.ok:
        status["error"] = r.error or f"HTTP {r.status}"
        return [], status
    try:
        fn = {"WMS": parse_wms, "WFS": parse_wfs, "WMTS": parse_wmts, "WCS": parse_wcs}[service]
        layers, _ = fn(r.body, base, ctx, r.ms)
    except Exception as e:
        status["error"] = f"parse: {type(e).__name__}: {e}"[:200]
        return [], status
    status["ok"] = True
    status["n_layers"] = len(layers)
    for L in layers:
        L.cors = r.cors
        if curated_licence and not L.licence_text:
            L.licence_text = curated_licence
    return layers[:max_layers], status


def _req_base(layer: Layer) -> str:
    """Where to send GetMap/GetFeature: the address the capabilities named for it, else the service address."""
    import json as _json

    try:
        u = (_json.loads(layer.endpoint_info or "{}") or {}).get("get_url") or ""
    except Exception:
        u = ""
    u = u.strip()
    if not u or not u.lower().startswith("http"):
        return layer.service_url
    u = base_url(u)
    return u


def _is_exception(body: bytes) -> bool:
    head = body[:3000]
    return b"ExceptionReport" in head or b"ServiceException" in head or b"<ows:Exception" in head


async def check_layer(c: Client, layer: Layer) -> tuple[str, str]:
    if layer.service_type in ("wmts", "wcs"):
        return "unchecked", "check not implemented for this protocol yet"
    if not layer.bbox:
        return "unchecked", "no bbox"
    x0, y0, x1, y1 = layer.bbox
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    dx, dy = max((x1 - x0) / 10, 1e-4), max((y1 - y0) / 10, 1e-4)
    b = _req_base(layer)
    sep = "&" if "?" in b else "?"
    if layer.service_type == "wms":
        url = (f"{b}{sep}SERVICE=WMS&REQUEST=GetMap&VERSION=1.1.1&LAYERS={layer.layer_name}&STYLES="
               f"&SRS=EPSG:4326&BBOX={cx-dx},{cy-dy},{cx+dx},{cy+dy}&WIDTH=64&HEIGHT=64&FORMAT=image/png&TRANSPARENT=true")
        r = await c.get(url, retries=0)
        if r.ok and "image" in r.content_type:
            return "ok", "image"
        if r.ok and _is_exception(r.body):
            return "fail", _exception_text(r.body)
        return "fail", r.error or f"HTTP {r.status} {r.content_type[:30]}"
    # WFS: 2.0.0 first (some servers refuse 1.1.0 without an outputFormat), then 1.1.0
    tries = [f"VERSION=2.0.0&TYPENAMES={layer.layer_name}&COUNT=1", f"VERSION=1.1.0&TYPENAME={layer.layer_name}&MAXFEATURES=1"]
    r = None
    for t in tries:
        r = await c.get(f"{b}{sep}SERVICE=WFS&REQUEST=GetFeature&{t}", retries=0)
        if r.ok and not _is_exception(r.body):
            return "ok", "feature"
    if r is not None and r.ok:
        return "fail", _exception_text(r.body)
    return "fail", (r.error if r is not None else "") or f"HTTP {r.status if r is not None else 0}"


def _exception_text(body: bytes) -> str:
    import re as _re

    m = _re.search(rb"<(?:\w+:)?(?:ServiceException|ExceptionText)[^>]*>(.*?)</", body[:5000], _re.S)
    t = (m.group(1) if m else body[:120]).decode("utf-8", "replace")
    return ("exception: " + " ".join(t.split()))[:120]
