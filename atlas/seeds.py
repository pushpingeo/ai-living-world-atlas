"""Turn the Dateno data portals registry (CC BY 4.0) into crawl targets for one or more countries."""
from __future__ import annotations

from collections import defaultdict
from urllib.parse import urlsplit

import duckdb

from .crawl_arcgis import services_root
from .crawl_ogc import base_url

REGISTRY_URL = "https://raw.githubusercontent.com/commondataio/dataportals-registry/main/data/datasets/full.parquet"

OWNER_TYPES = {
    "Central government": "central-gov", "Regional government": "regional-gov", "Local government": "local-gov",
    "Academy": "academic", "Business": "business", "Civil society": "civil-society", "International": "international",
}


def load_targets(parquet: str, countries: list[str]) -> dict:
    con = duckdb.connect()
    cc = ",".join(f"'{c}'" for c in countries)
    rows = con.execute(f"""
        SELECT id, name, link, owner.name AS owner, owner.type AS owner_type, software.id AS sw,
               list_transform(coverage, lambda x: x.location.country.id) AS cc, endpoints, status
        FROM '{parquet}'
        WHERE list_has_any(list_transform(coverage, lambda x: x.location.country.id), [{cc}])
          AND coalesce(status, 'active') = 'active'
    """).fetchall()
    t = {"arcgis_roots": {}, "wms": {}, "wfs": {}, "wmts": {}, "wcs": {}, "hub": {}, "ckan": {}, "catalogues": len(rows)}
    by_sw = defaultdict(int)
    for cid, name, link, owner, otype, sw, ccs, endpoints, status in rows:
        ctx = {
            "publisher": owner or name or "", "publisher_type": OWNER_TYPES.get(otype or "", "unknown"),
            "country": next((c for c in (ccs or []) if c in countries), countries[0]), "seed_catalog": cid,
            "discovered_via": "registry",
        }
        eps = {e["type"]: e["url"] for e in (endpoints or []) if e and e.get("url")}
        used = False
        if "arcgis:rest:services" in eps or sw == "arcgisserver":
            root = services_root(eps.get("arcgis:rest:services") or link or "")
            if root:
                t["arcgis_roots"].setdefault(root, ctx)
                used = True
        for key in ("wms130", "wms111", "ogc:wms", "geoserver:wms"):
            if key in eps:
                t["wms"].setdefault(base_url(eps[key]), ctx)
                used = True
                break
        for key in ("wfs200", "wfs110", "wfs100", "ogc:wfs"):
            if key in eps:
                t["wfs"].setdefault(base_url(eps[key]), ctx)
                used = True
                break
        if "wmts100" in eps:
            t["wmts"].setdefault(base_url(eps["wmts100"]), ctx)
            used = True
        for key in ("wcs201", "wcs111", "wcs110", "wcs11", "wcs100"):
            if key in eps:
                t["wcs"].setdefault(base_url(eps[key]), ctx)
                used = True
                break
        if sw == "arcgishub" and ("dcatus11" in eps or link):
            # /data.json is unreliable on Hub sites; the dcat-us feed path works
            p = urlsplit(eps.get("dcatus11") or link)
            feed = f"{p.scheme or 'https'}://{p.netloc}/api/feed/dcat-us/1.1.json"
            t["hub"].setdefault(feed, {**ctx, "discovered_via": f"hub:{link}"})
            used = True
        if "ckan:package-search" in eps:
            t["ckan"].setdefault(eps["ckan:package-search"], {**ctx, "discovered_via": f"ckan:{link}", "portal": link})
            used = True
        if used:
            by_sw[sw or "?"] += 1
    t["used_by_software"] = dict(by_sw)
    return t
