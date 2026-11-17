"""Harvest catalogue records (ArcGIS Hub DCAT-US feeds, CKAN) for their links to live services.

Catalogue records often carry the best metadata (licence, theme, a proper description),
and they tell us which services a public body actually stands behind.
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from urllib.parse import parse_qsl, urlsplit

from .crawl_arcgis import service_url_of, services_root
from .crawl_ogc import base_url
from .net import Client
from .record import clean_text, norm_url


@dataclass
class PortalRecord:
    portal: str
    title: str
    abstract: str
    licence: str
    keywords: list[str]
    themes: list[str]
    publisher: str
    landing_page: str
    links: list[tuple[str, str]] = field(default_factory=list)  # (kind, url) kind in arcgis|wms|wfs
    scale: float | None = None  # scale denominator stated in the metadata (ISO/INSPIRE)
    country: str = ""  # ISO2, when the catalogue states it per record
    layer_names: list[tuple[str, str]] = field(default_factory=list)  # (OGC server base, layer name) the record names


def ogc_layer_key(url: str, name: str) -> tuple[str, str]:
    """(server base, layer name) that a WMS, WFS, WMTS or WCS layer shares across protocols on one server."""
    u = re.sub(r"^https?://", "", url.lower().split("?")[0].split("#")[0].rstrip("/"))
    u = re.sub(r"/(wms|wfs|wmts|wcs|ows|gwc/service/wmts|gwc/service/wms)$", "", u)
    return u, str(name).strip().split(":")[-1].lower()


def classify_link(url: str, fmt: str = "") -> tuple[str, str] | None:
    """Return (kind, canonical service/layer url) for a link that points at a map service."""
    try:
        return _classify(url, fmt)
    except ValueError:  # malformed URLs are common in catalogue records
        return None


def _classify(url: str, fmt: str) -> tuple[str, str] | None:
    if not url or not url.startswith("http"):
        return None
    u = url.strip()
    low = u.lower()
    f = (fmt or "").lower()
    if "/rest/services" in low:
        return ("arcgis", u.split("?")[0].rstrip("/"))
    q = {k.lower(): v.lower() for k, v in parse_qsl(urlsplit(u).query)}
    svc = q.get("service", "")
    if svc == "wmts" or f in ("wmts", "ogc wmts") or re.search(r"/wmts/?$|/wmts/1\.0\.0/", urlsplit(low).path):
        return ("wmts", base_url(u.split("/1.0.0/")[0]) if "/1.0.0/" in u else base_url(u))
    if svc == "wcs" or f in ("wcs", "ogc wcs") or re.search(r"/wcs/?$", urlsplit(low).path):
        return ("wcs", base_url(u))
    if svc == "wms" or f in ("wms", "ogc wms") or re.search(r"/wms(server)?/?$", urlsplit(low).path):
        return ("wms", base_url(u))
    if svc == "wfs" or f in ("wfs", "ogc wfs") or re.search(r"/wfs(server)?/?$", urlsplit(low).path):
        return ("wfs", base_url(u))
    if re.search(r"/ows/?$", urlsplit(low).path):
        return ("wms", base_url(u))
    return None


def _placeholder(s: str) -> str:
    """Hub feeds leave template tokens like {{source}} when the org never filled them in."""
    return "" if re.fullmatch(r"\s*\{\{[^}]*\}\}\s*", s or "") else (s or "")


async def harvest_hub(c: Client, feed_url: str, portal: str) -> tuple[list[PortalRecord], dict]:
    st = {"portal": portal, "kind": "hub", "ok": False, "error": "", "records": 0}
    r = await c.get(feed_url)
    if not r.ok:
        st["error"] = r.error or f"HTTP {r.status}"
        return [], st
    try:
        j = r.json()
    except Exception:
        st["error"] = "not json"
        return [], st
    out = []
    for d in j.get("dataset") or []:
        links = []
        for dist in d.get("distribution") or []:
            k = classify_link(dist.get("accessURL") or "", dist.get("format") or "")
            if k:
                links.append(k)
        if not links:
            continue
        theme = d.get("theme") or []
        out.append(PortalRecord(
            portal=portal, title=clean_text(d.get("title")), abstract=clean_text(d.get("description")),
            licence=clean_text(d.get("license")), keywords=[k for k in (d.get("keyword") or []) if isinstance(k, str)][:30],
            themes=[t for t in (theme if isinstance(theme, list) else [theme]) if t],
            publisher=_placeholder(((d.get("publisher") or {}).get("name") or "")),
            landing_page=d.get("landingPage") or "", links=links,
        ))
    st.update(ok=True, records=len(out), total=len(j.get("dataset") or []))
    return out, st


async def harvest_ckan(c: Client, search_url: str, portal: str, max_records: int = 200_000, page: int = 1000) -> tuple[list[PortalRecord], dict]:
    st = {"portal": portal, "kind": "ckan", "ok": False, "error": "", "records": 0, "scanned": 0}
    out: list[PortalRecord] = []
    start = 0
    while start < max_records:
        sep = "&" if "?" in search_url else "?"
        r = await c.get(f"{search_url}{sep}rows={page}&start={start}", retries=2)
        if not r.ok:
            st["error"] = r.error or f"HTTP {r.status} at start={start}"
            break
        try:
            res = r.json()["result"]
        except Exception:
            st["error"] = f"bad json at start={start}"
            break
        rows = res.get("results") or []
        st["count"] = res.get("count")
        st["scanned"] += len(rows)
        for p in rows:
            links = []
            for res_ in p.get("resources") or []:
                k = classify_link(res_.get("url") or "", res_.get("format") or "")
                if k:
                    links.append(k)
            if not links:
                continue
            extras = {e.get("key"): e.get("value") for e in (p.get("extras") or []) if isinstance(e, dict)}
            themes = [v for k, v in extras.items() if k and re.search(r"theme|topic", k, re.I) and v]
            if p.get("theme-primary"):
                themes.append(p["theme-primary"])
            org = p.get("organization") or {}
            out.append(PortalRecord(
                portal=portal, title=clean_text(p.get("title")), abstract=clean_text(p.get("notes")),
                licence=clean_text(p.get("license_title") or p.get("license_id") or extras.get("licence") or ""),
                keywords=[t.get("display_name") or t.get("name") for t in (p.get("tags") or []) if isinstance(t, dict)][:30],
                themes=[str(t) for t in themes][:10], publisher=clean_text(org.get("title") or ""),
                landing_page=f"{portal.rstrip('/')}/dataset/{p.get('name')}", links=links,
            ))
        if len(rows) < page:
            break
        start += page
    st["ok"] = st["scanned"] > 0
    st["records"] = len(out)
    return out, st


def service_targets(rec: PortalRecord) -> list[tuple[str, str]]:
    """Which services to crawl for this record: (kind, url). ArcGIS links -> the specific service."""
    out = []
    for kind, u in rec.links:
        if kind == "arcgis":
            s = service_url_of(u)
            if s:
                out.append(("arcgis-service", s))
            elif services_root(u):
                out.append(("arcgis-root", services_root(u)))
        else:
            out.append((kind, u))
    return out


AGOL_TYPES = ["Feature Service", "Map Service", "Image Service", "Vector Tile Service", "WMS", "WMTS", "WFS"]
PAID = ("requires subscription", "requires credits", "subscriber", "premium")


async def harvest_arcgis_online(c: Client, query: str, portal: str, max_records: int = 60_000) -> tuple[list[PortalRecord], dict]:
    """Public ArcGIS Online items for a query (e.g. a Living Atlas group), split by item type to get past
    the 10,000-results-per-query cap. Items that need a subscription or credits are skipped."""
    from urllib.parse import quote

    st = {"portal": portal, "kind": "arcgis-online", "ok": False, "error": "", "records": 0, "scanned": 0, "skipped_paid": 0}
    out: list[PortalRecord] = []
    for typ in AGOL_TYPES:
        start = 1
        while start > 0 and start <= 10_000 and st["scanned"] < max_records:
            q = quote(f'{query} type:"{typ}" access:public')
            r = await c.get(f"https://www.arcgis.com/sharing/rest/search?q={q}&num=100&start={start}&sortField=modified&f=json", retries=2)
            if not r.ok:
                st["error"] = r.error or f"HTTP {r.status}"
                break
            try:
                j = r.json()
            except Exception:
                st["error"] = "not json"
                break
            for it in j.get("results") or []:
                st["scanned"] += 1
                if it.get("type") != typ or not it.get("url"):
                    continue
                kws = " ".join(it.get("typeKeywords") or []).lower()
                if any(p in kws for p in PAID):
                    st["skipped_paid"] += 1
                    continue
                k = classify_link(it["url"], "WMS" if typ == "WMS" else "WMTS" if typ == "WMTS" else "WFS" if typ == "WFS" else "")
                if not k:
                    continue
                ext = it.get("extent") or []
                credits = clean_text(it.get("accessInformation") or "")
                out.append(PortalRecord(
                    portal=portal, title=clean_text(it.get("title")),
                    abstract=clean_text(it.get("description") or it.get("snippet") or ""),
                    licence=clean_text(it.get("licenseInfo") or ""), keywords=(it.get("tags") or [])[:30], themes=[],
                    publisher=(credits[:120] if credits else it.get("owner", "")),
                    landing_page=f"https://www.arcgis.com/home/item.html?id={it.get('id')}", links=[k],
                ))
            start = j.get("nextStart", -1)
    st.update(ok=st["scanned"] > 0, records=len(out))
    return out, st


GN_FIELDS = ["uuid", "resourceTitleObject", "resourceAbstractObject", "link", "cl_topic", "resourceType",
             "th_httpinspireeceuropaeutheme-theme", "OrgForResourceObject", "licenseObject",
             "MD_LegalConstraintsOtherConstraintsObject", "resolutionScaleDenominator", "tag", "geom"]
GN_PROTOCOLS = ["OGC:WMS", "OGC:WFS", "OGC:WMTS", "OGC:WCS", "ESRI:REST", "ESRI:ArcGIS",
                "OGC:WMS-1.1.1-http-get-map", "OGC:WMS-1.3.0-http-get-map", "OGC:WFS-1.0.0-http-get-capabilities"]


def _gn_text(v) -> str:
    """Text from a GeoNetwork field: a string, a {"default"/"langeng"/"key": ...} object, or a list of either.
    Newer GeoNetwork (EMODnet, 2026) returns codelists such as cl_topic as objects, so always end with a string."""
    if isinstance(v, dict):
        return _gn_text(v.get("langeng") or v.get("default") or v.get("key") or next(iter(v.values()), ""))
    if isinstance(v, list):
        return "; ".join(x for x in (_gn_text(x) for x in v if x) if x)
    return v if isinstance(v, str) else (str(v) if v is not None else "")


async def harvest_geonetwork(c: Client, base: str, portal: str, max_records: int = 400_000, page: int = 500) -> tuple[list[PortalRecord], dict]:
    """GeoNetwork 4 search API (Elasticsearch), paged with search_after. Keeps records that link a map service.
    INSPIRE metadata carries ISO topic categories, INSPIRE themes and a stated scale, which we keep."""
    import json as _json

    st = {"portal": portal, "kind": "geonetwork", "ok": False, "error": "", "records": 0, "scanned": 0}
    url = base.rstrip("/") + "/srv/api/search/records/_search"
    out: list[PortalRecord] = []
    after = None
    while st["scanned"] < max_records:
        body = {"size": page, "sort": [{"uuid": "asc"}], "_source": {"includes": GN_FIELDS}, "track_total_hits": True,
                "query": {"bool": {"filter": [{"terms": {"linkProtocol": GN_PROTOCOLS}}]}}}
        if after:
            body["search_after"] = after
        r = await c.post_json(url, body)
        if not r.ok:
            st["error"] = r.error or f"HTTP {r.status}: {r.body[:120]!r}"
            break
        try:
            j = r.json()
        except Exception:
            st["error"] = "not json"
            break
        hits = (j.get("hits") or {}).get("hits") or []
        st["total"] = ((j.get("hits") or {}).get("total") or {}).get("value")
        if not hits:
            break
        for h in hits:
            st["scanned"] += 1
            s = h.get("_source") or {}
            links, names = [], []
            for ln in s.get("link") or []:
                u = _gn_text(ln.get("urlObject")) or ln.get("url") or ""
                k = classify_link(u, (ln.get("protocol") or "").replace("OGC:", "").split("-")[0])
                if k:
                    links.append(k)
                    # the layer the record describes, e.g. emodnet:heritageshipwrecks on a 200-layer WMS/WFS server
                    nm = _gn_text(ln.get("nameObject")) or ln.get("name") or ""
                    if k[0] in ("wms", "wfs", "wmts", "wcs") and isinstance(nm, str) and nm.strip():
                        names.append((ogc_layer_key(k[1], nm)))
            if not links:
                continue
            themes = list(dict.fromkeys([_gn_text(x) for x in (s.get("cl_topic") or [])] +
                                        [_gn_text(t) for t in (s.get("th_httpinspireeceuropaeutheme-theme") or [])]))
            scale = s.get("resolutionScaleDenominator")
            scale = scale[0] if isinstance(scale, list) and scale else scale
            lic = _gn_text(s.get("licenseObject")) or _gn_text(s.get("MD_LegalConstraintsOtherConstraintsObject"))
            out.append(PortalRecord(
                portal=portal, title=_gn_text(s.get("resourceTitleObject")), abstract=clean_text(_gn_text(s.get("resourceAbstractObject"))),
                licence=clean_text(lic)[:600], keywords=[_gn_text(t) for t in (s.get("tag") or [])][:30], themes=themes[:10],
                publisher=_gn_text(s.get("OrgForResourceObject"))[:150],
                landing_page=f"{base.rstrip('/')}/srv/api/records/{s.get('uuid') or h.get('_id')}",
                links=list(dict.fromkeys(links)), scale=float(scale) if scale else None,
                layer_names=list(dict.fromkeys(names)),
            ))
        after = hits[-1].get("sort")
        if not after:
            break
    st.update(ok=st["scanned"] > 0, records=len(out))
    return out, st


# ---------------- data.europa.eu (piveau hub-search) ----------------
# Since late 2026 the INSPIRE geoportal redirects here; data.europa.eu harvests the national INSPIRE
# catalogues (gdi-de, rndt, ngr-nl, idee, ...) and exposes them through one search API.
DEU_FORMATS = ["WMS_SRVC", "WFS_SRVC", "WMTS_SRVC", "OGCFEAT", "REST"]
DEU_FIELDS = "id,title,description,publisher,distributions,keywords,categories,landing_page,catalog.id,country.id"


def _ml(v) -> str:
    """Pick English from a multilingual field, else the first language given."""
    if isinstance(v, dict):
        return v.get("en") or next((x for x in v.values() if x), "")
    if isinstance(v, list):
        return _ml(v[0]) if v else ""
    return v or ""


def _deu_record(d: dict, portal: str) -> PortalRecord | None:
    links, lic = [], ""
    for dist in d.get("distributions") or []:
        fmt = ((dist.get("format") or {}).get("id") or "").replace("_SRVC", "")
        for u in (dist.get("access_url") or []) if isinstance(dist.get("access_url"), list) else [dist.get("access_url") or ""]:
            k = classify_link(u or "", fmt)
            if k:
                links.append(k)
                l = dist.get("license") or {}
                lic = lic or (l.get("label") or l.get("id") or "") if isinstance(l, dict) else lic
    if not links:
        return None
    pub = d.get("publisher") or {}
    lp = d.get("landing_page") or []
    lp = (lp[0].get("resource") if lp and isinstance(lp[0], dict) else "") or f"https://data.europa.eu/data/datasets/{d.get('id')}"
    return PortalRecord(
        portal=portal, title=clean_text(_ml(d.get("title"))), abstract=clean_text(_ml(d.get("description"))),
        licence=clean_text(lic)[:600],
        keywords=[k.get("label") for k in (d.get("keywords") or []) if isinstance(k, dict) and k.get("label")][:30],
        themes=["eu-theme:" + c["id"] for c in (d.get("categories") or []) if isinstance(c, dict) and c.get("id")][:10],
        publisher=clean_text(pub.get("name") if isinstance(pub, dict) else "")[:150],
        landing_page=lp, links=list(dict.fromkeys(links)),
        country=((d.get("country") or {}).get("id") or "").upper() if isinstance(d.get("country"), dict) else "",
    )


async def harvest_data_europa(c: Client, base: str, portal: str, max_records: int = 2_000_000, page: int = 500,
                              deadline: float | None = None) -> tuple[list[PortalRecord], dict]:
    """Scroll through data.europa.eu datasets that have a map/feature service distribution, one format at a time."""
    import json as _json
    import time as _time
    from urllib.parse import quote

    api = base.rstrip("/") + "/api/hub/search"
    st = {"portal": portal, "kind": "data-europa", "ok": False, "error": "", "records": 0, "scanned": 0, "by_format": {}}
    seen: dict[str, PortalRecord] = {}
    # A scroll is a server-side cursor: a bad page can't be asked for again (the cursor has moved on), and the
    # Nov 2026 run lost over half the WMS/WFS records that way. So when a scroll breaks, start that format again
    # from the top and skip what we already have; re-reading 150k ids costs a few minutes.
    restarts_max = 6
    for fmt in DEU_FORMATS:
        facets = quote(_json.dumps({"format": [fmt]}))
        first = f"{api}/search?filter=dataset&limit={page}&scroll=true&facets={facets}&includes={DEU_FIELDS}"
        ids_fmt: set = set()
        total = None
        for restart in range(restarts_max + 1):
            url, n, broke = first, 0, False
            while url and st["scanned"] < max_records:
                if deadline and _time.monotonic() > deadline:
                    st["error"] = (st["error"] + f" time budget hit in {fmt};").strip()
                    url = None
                    break
                res = None
                for attempt in range(3):
                    # pages can be big (records with hundreds of distributions): don't let the size cap cut them
                    r = await c.get(url, retries=3, timeout=180, max_bytes=300_000_000)
                    try:
                        res = r.json()["result"] if r.ok else None
                    except Exception:
                        res = None
                    if res is not None:
                        break
                    await asyncio.sleep(10 * (attempt + 1))
                if res is None:
                    body = (r.body or b"")[:120].decode("utf-8", "replace").replace("\n", " ")
                    st["error"] += f" {fmt}: {r.error or 'HTTP ' + str(r.status)} after {n} [{len(r.body or b'')} bytes: {body}];"
                    broke = True
                    break
                rows = res.get("results") or []
                total = res.get("count", total)
                for d in rows:
                    n += 1
                    did = d.get("id")
                    if did in ids_fmt:
                        continue
                    ids_fmt.add(did)
                    st["scanned"] += 1
                    rec = _deu_record(d, portal)
                    if rec is None:
                        continue
                    prev = seen.get(did)
                    if prev:
                        prev.links = list(dict.fromkeys(prev.links + rec.links))
                    else:
                        seen[did] = rec
                sid = res.get("scrollId")
                url = f"{api}/scroll?scrollId={quote(sid)}" if (rows and sid) else None
            if deadline and _time.monotonic() > deadline:
                break
            # asking again for a page may have moved the cursor past it, so a scroll that "finished" can still
            # have holes: check the count against the total the API reported
            short = bool(total) and len(ids_fmt) < 0.995 * total and st["scanned"] < max_records
            if not broke and not short:
                break
            st["error"] += f" {fmt}: restart {restart + 1} with {len(ids_fmt)} of {total} kept;"
            await asyncio.sleep(30)
        st.setdefault("totals", {})[fmt] = total
        st["by_format"][fmt] = len(ids_fmt)
    out = list(seen.values())
    st.update(ok=st["scanned"] > 0, records=len(out))
    return out, st
