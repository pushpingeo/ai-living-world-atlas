"""Harvest catalogue records (ArcGIS Hub DCAT-US feeds, CKAN) for their links to live services.

Catalogue records often carry the best metadata (licence, theme, a proper description),
and they tell us which services a public body actually stands behind.
"""
from __future__ import annotations

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


def classify_link(url: str, fmt: str = "") -> tuple[str, str] | None:
    """Return (kind, canonical service/layer url) for a link that points at a map service."""
    if not url or not url.startswith("http"):
        return None
    u = url.strip()
    low = u.lower()
    f = (fmt or "").lower()
    if "/rest/services" in low:
        return ("arcgis", u.split("?")[0].rstrip("/"))
    q = {k.lower(): v.lower() for k, v in parse_qsl(urlsplit(u).query)}
    svc = q.get("service", "")
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
