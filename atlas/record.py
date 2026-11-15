"""The layer record: one row per queryable/displayable layer, whatever the service type.

Publisher text is stored verbatim. Anything we derive goes in its own field.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from urllib.parse import urlsplit, urlunsplit


def norm_url(u: str) -> str:
    """Lower-case scheme/host, drop query and trailing slash, unify /arcgis/rest case."""
    p = urlsplit(u.strip())
    path = re.sub(r"/+$", "", p.path)
    path = re.sub(r"/arcgis/rest/services", "/arcgis/rest/services", path, flags=re.I)
    return urlunsplit((p.scheme.lower() or "https", p.netloc.lower(), path, "", ""))


def clean_text(v) -> str:
    """Strip HTML tags and entities, collapse whitespace. Wording is left untouched."""
    import html

    if v is None:
        return ""
    s = str(v)
    s = re.sub(r"<(br|/p|/div|/li)\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s).replace("\xa0", " ")
    s = re.sub(r"[ \t\r\f\v]+", " ", s)
    s = re.sub(r"\s*\n\s*", "\n", s)
    return s.strip()


def uid(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:16]


@dataclass
class Layer:
    layer_url: str                 # canonical address of the layer
    service_url: str
    service_type: str              # arcgis-featureserver | arcgis-mapserver | arcgis-imageserver | wms | wfs
    layer_name: str                # WMS/WFS Name or ArcGIS layer id
    title: str = ""
    abstract: str = ""             # verbatim from publisher
    keywords: list[str] = field(default_factory=list)
    service_title: str = ""
    service_abstract: str = ""
    licence_text: str = ""         # verbatim: copyrightText / AccessConstraints / Fees / portal licence
    publisher: str = ""
    publisher_type: str = ""       # central-gov | regional-gov | local-gov | academic | business | civil-society | unknown
    country: str = ""
    seed_catalog: str = ""         # Dateno registry id or portal we found it through
    discovered_via: str = ""       # registry | ckan:<portal> | hub:<site>
    listed_by: str = ""            # who listed it, when that isn't the publisher (a Hub linking someone else's service)
    geometry_type: str = ""
    fields: list[str] = field(default_factory=list)   # "name|alias|type"
    native_crs: str = ""
    bbox: list[float] | None = None                   # WGS84 [xmin, ymin, xmax, ymax]
    declared_themes: list[str] = field(default_factory=list)  # as stated by source (ISO topic, INSPIRE, DCAT)
    landing_page: str = ""
    portal_title: str = ""         # title of the catalogue record that links to this service
    portal_abstract: str = ""
    portal_licence: str = ""
    metadata_url: str = ""
    has_time: bool = False
    # resolution signals, stored raw; see atlas/resolution.py for how they become a detail level
    scale_finest: float | None = None      # smallest scale denominator the publisher shows it at
    scale_coarsest: float | None = None    # largest scale denominator it is shown at
    cache_finest_scale: float | None = None  # finest tile-cache level, as a scale denominator
    pixel_size_m: float | None = None      # raster cell size
    # what this endpoint can do, in plain verbs an agent can filter on:
    # query, download, render, tiles, feature-info, pixels, catalog, raster-functions, time, multidimensional
    capabilities: list[str] = field(default_factory=list)
    endpoint_info: str = ""                # JSON: protocol specifics (max records, formats, bands, tiling scheme...)
    role: str = "data"                     # data | imagery | elevation | basemap
    crawled_at: str = ""
    service_ms: int = 0

    @property
    def uid(self) -> str:
        return uid(norm_url(self.layer_url), self.layer_name)

    def to_row(self) -> dict:
        d = asdict(self)
        d["uid"] = self.uid
        return d


# ---- coordinate helpers -------------------------------------------------

ESRI_ALIASES = {102100: 3857, 102113: 3857, 900913: 3857, 102003: 5070}


@lru_cache(maxsize=512)
def _transformer(src: str):
    from pyproj import CRS, Transformer

    return Transformer.from_crs(CRS.from_user_input(src), CRS.from_epsg(4326), always_xy=True)


def to_wgs84(xmin, ymin, xmax, ymax, wkid=None, wkt=None) -> list[float] | None:
    try:
        vals = [float(v) for v in (xmin, ymin, xmax, ymax)]
    except (TypeError, ValueError):
        return None
    if any(v != v or abs(v) > 1e15 for v in vals):  # NaN or junk
        return None
    if vals[0] >= vals[2] or vals[1] >= vals[3]:
        return None
    if wkid in (None, 4326, 4258, 4269) and not wkt:
        out = vals
    else:
        try:
            src = wkt or (f"EPSG:{ESRI_ALIASES.get(wkid, wkid)}")
            try:
                t = _transformer(src)
            except Exception:
                t = _transformer(f"ESRI:{wkid}")
            out = list(t.transform_bounds(*vals, densify_pts=11))
        except Exception:
            return None
    out = [max(-180, out[0]), max(-90, out[1]), min(180, out[2]), min(90, out[3])]
    if out[0] >= out[2] or out[1] >= out[3]:
        return None
    return [round(v, 6) for v in out]
