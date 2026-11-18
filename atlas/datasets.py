"""Group endpoints (layers) into datasets: one entry per dataset, with every way to reach it.

Strong rules (same data, near certain):
  arcgis-pair     MapServer/N and FeatureServer/N of the same ArcGIS service
  arcgis-ogc      an ArcGIS service's own WMS/WFS/WMTS facade (.../services/X/MapServer/WMSServer)
  ogc-name        WMS, WFS, WMTS and WCS on one server publishing the same layer name
  catalogue       links in one catalogue record whose layers carry the same title
Weak rule (probably the same data, recorded as such):
  title-extent    same title and publisher, extents overlapping by 80%+
"""
from __future__ import annotations

import json
import re
from collections import defaultdict

import pandas as pd

PROTOCOL_PREF = ["arcgis-featureserver", "wfs", "geojson", "arcgis-imageserver", "wcs", "arcgis-mapserver", "wms",
                 "arcgis-vectortileserver", "wmts"]
ROLE_PREF = ["imagery", "elevation", "basemap", "data"]


class UF:
    def __init__(self, n):
        self.p = list(range(n))
        self.size = [1] * n

    def find(self, a):
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]
            a = self.p[a]
        return a

    def union(self, a, b, cap: int | None = None):
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False
        if cap and self.size[ra] + self.size[rb] > cap:
            return False  # title-based joins that would snowball are more likely wrong than right
        lo, hi = min(ra, rb), max(ra, rb)
        self.p[hi] = lo
        self.size[lo] += self.size[hi]
        return True


def _ntitle(t: str) -> str:
    t = re.sub(r"\(?©[^)]*\)?", "", str(t or "").lower())
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def _arc_base(url: str) -> str | None:
    """ArcGIS REST or SOAP/OGC URL -> host/path/Folder/Name (no service type)."""
    u = url.lower().split("?")[0].split("#")[0]
    m = re.search(r"^https?://([^/]+/.*?)/(?:rest/)?services/(.+?)/(mapserver|featureserver|imageserver)", u)
    return f"{m.group(1)}|{m.group(2)}" if m else None


def _ogc_base(url: str) -> str:
    u = url.lower().split("?")[0].split("#")[0].rstrip("/")
    u = re.sub(r"^https?://", "", u)
    return re.sub(r"/(wms|wfs|wmts|wcs|ows|gwc/service/wmts|gwc/service/wms)$", "", u)


def _iou(a, b) -> float:
    if a is None or b is None:
        return 0.0
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[2], b[2]), min(a[3], b[3])
    if x1 <= x0 or y1 <= y0:
        return 0.0
    inter = (x1 - x0) * (y1 - y0)
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


def group(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Returns (dataset_key per row, rule that joined it) aligned to df.index."""
    n = len(df)
    uf = UF(n)
    rule = [""] * n
    rows = df.reset_index(drop=True)
    st = rows["service_type"].tolist()
    url = rows["service_url"].tolist()
    lname = rows["layer_name"].astype(str).str.lower().tolist()
    # raw layer titles, not catalogue-substituted ones: a catalogue title is shared by every layer it links
    title = [_ntitle(t) for t in rows["title"].tolist()]
    meaningful = [bool(t) and len(t) >= 6 and not t.replace(" ", "").isdigit() and " " in t for t in title]

    def join(members, label, cap=None):
        for m in members[1:]:
            if uf.union(members[0], m, cap):
                rule[m] = rule[m] or label
                rule[members[0]] = rule[members[0]] or label

    # arcgis-pair and arcgis-ogc: key on the ArcGIS service base + layer id, or + title
    keys = defaultdict(list)
    tkeys = defaultdict(list)
    for i in range(n):
        b = _arc_base(url[i])
        if not b:
            continue
        # layer ids only line up between REST services; an ArcGIS WMS numbers its layers differently
        if st[i].startswith("arcgis"):
            keys[(b, lname[i])].append(i)
        if title[i]:
            tkeys[(b, title[i])].append(i)
    for k, members in keys.items():
        if len({st[m] for m in members}) > 1:
            join(members, "arcgis-pair")
    for k, members in tkeys.items():
        protos = [st[m] for m in members]
        # only when unambiguous: each protocol appears once
        if len(set(protos)) > 1 and len(set(protos)) == len(protos) and any(not p.startswith("arcgis") for p in protos):
            join(members, "arcgis-ogc")

    # ogc-name: same server, same published name, different protocols
    okeys = defaultdict(list)
    for i in range(n):
        if st[i] in ("wms", "wfs", "wmts", "wcs"):
            okeys[(_ogc_base(url[i]), lname[i].split(":")[-1] if ":" in lname[i] else lname[i])].append(i)
    for k, members in okeys.items():
        if len({st[m] for m in members}) > 1:
            join(members, "ogc-name")

    # catalogue: same record, same title
    ckeys = defaultdict(list)
    for i, lp in enumerate(rows["landing_page"].fillna("").tolist()):
        if lp and meaningful[i]:
            ckeys[(lp, title[i])].append(i)
    for members in ckeys.values():
        if len(members) > 1:
            join(members, "catalogue", cap=8)

    # title-extent (weak)
    pub = [_ntitle(p) for p in rows["publisher"].fillna("").tolist()]
    bbox = rows["_bbox"].tolist()
    gkeys = defaultdict(list)
    for i in range(n):
        if meaningful[i]:
            gkeys[(title[i], pub[i])].append(i)
    for members in gkeys.values():
        if 1 < len(members) <= 200:
            for a_i, a in enumerate(members):
                for b in members[a_i + 1:]:
                    if uf.find(a) != uf.find(b) and _iou(bbox[a], bbox[b]) >= 0.8:
                        if uf.union(a, b, cap=8):
                            rule[b] = rule[b] or "title-extent"
                            rule[a] = rule[a] or "title-extent"

    roots = [uf.find(i) for i in range(n)]
    return pd.Series(roots, index=df.index), pd.Series(rule, index=df.index)


def build(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """df: scored layer rows with a '_bbox' list column. Returns (df with dataset_id, datasets)."""
    root, rule = group(df)
    df = df.copy()
    df["_root"] = root.values
    df["dataset_match"] = rule.values
    pref = {p: i for i, p in enumerate(PROTOCOL_PREF)}
    out = []
    ids = {}
    for r, g in df.groupby("_root", sort=False):
        g = g.assign(_p=g["service_type"].map(lambda s: pref.get(s, 99)))
        best = g.sort_values(["q_pass", "q_total", "_p"], ascending=[False, False, True]).iloc[0]
        ids[r] = best["uid"]
        abstracts = [a for a in list(g["abstract"]) + list(g["portal_abstract"]) if isinstance(a, str) and a]
        roles = set(g["role"])
        eps = [{
            "uid": e.uid, "protocol": e.service_type, "url": e.layer_url, "service_url": e.service_url,
            "layer_name": str(e.layer_name), "capabilities": list(e.capabilities), "check": e.check_status,
            "info": e.endpoint_info or "", "cors": None if pd.isna(getattr(e, "cors", None)) else bool(e.cors),
        } for e in g.sort_values("_p").itertuples()]
        details = g.dropna(subset=["detail_m"]).sort_values("detail_m")
        out.append({
            "dataset_id": best["uid"], "title": best["display_title"], "abstract": max(abstracts, key=len) if abstracts else "",
            "publisher": best["publisher"], "publisher_type": best["publisher_type_resolved"], "country": best["country"],
            "licence": best["portal_licence"] or best["licence_text"],
            "open_licence": bool(g["q_open_licence"].any()),
            "keywords": sorted({k for ks in g["keywords"] for k in ks})[:40],
            "iso_themes_declared": sorted({k for ks in g["iso_themes_declared"] for k in ks}),
            "landing_page": next((x for x in g["landing_page"] if x), ""),
            "role": next(rl for rl in ROLE_PREF if rl in roles),
            "coverage_level": best["coverage_level"],
            "extent_source": best.get("extent_source", "declared"),
            "extent_flags": list(best.get("extent_flags") if best.get("extent_flags") is not None else []),
            "detail_m": float(details.iloc[0]["detail_m"]) if len(details) else None,
            "detail_level": details.iloc[0]["detail_level"] if len(details) else "",
            "detail_source": details.iloc[0]["detail_source"] if len(details) else "",
            "protocols": sorted(set(g["service_type"]), key=lambda s: pref.get(s, 99)),
            "capabilities": sorted({c for cs in g["capabilities"] for c in cs}),
            "n_endpoints": len(g), "match_rules": sorted(set(g["dataset_match"]) - {""}),
            "q_total": int(g["q_total"].max()), "q_pass": bool(g["q_pass"].any()),
            "endpoints": json.dumps(eps, separators=(",", ":")),
            "_bbox": best["_bbox"],
        })
    df["dataset_id"] = df["_root"].map(ids)
    return df.drop(columns=["_root"]), pd.DataFrame(out)
