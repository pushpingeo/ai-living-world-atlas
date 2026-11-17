"""Title fixes applied at publish time (combine.py); the wave files keep what was crawled.

Status words in the service name: some publishers give a layer a plain title while the service it sits in says what
it really holds. NSTA's "UKCS offshore infrastructure pipeline linear (WGS84)" is the only layer of
UKCS_offshore_infrastructure_pipeline_linear_removed_(WGS84): removed pipelines, not live ones. When every endpoint of
a dataset sits in a service (ArcGIS) or layer (OGC) whose name carries one of these words and the title doesn't, the
word is added to the title. Asked for by Tobler, 17 Nov 2026.
"""
from __future__ import annotations

import json
import re
from urllib.parse import unquote

import pandas as pd

# "historic", "former" and "draft" are left out: in service names they mostly mean heritage ("Historic_Environment"),
# old boundaries or a work folder, and would mislabel live data.
STATUS_WORDS = ["removed", "decommissioned", "abandoned", "proposed", "planned", "superseded", "obsolete", "archived",
                "expired", "relinquished"]
_WORD = re.compile(r"(?<![a-z])(" + "|".join(STATUS_WORDS) + r")(?![a-z])", re.I)


def _names(ep: dict) -> str:
    """The publisher's own naming for where this endpoint lives: ArcGIS service name, or OGC layer name."""
    u = unquote(ep.get("service_url") or ep.get("url") or "")
    m = re.search(r"/rest/services/(.+?)/(Feature|Map|Image|VectorTile)Server", u, re.I)
    if m:
        return m.group(1).split("/")[-1]
    return str(ep.get("layer_name") or "")


def status_words(endpoints_json: str) -> list[str]:
    try:
        eps = json.loads(endpoints_json or "[]")
    except Exception:
        return []
    if not eps:
        return []
    per = [{w.lower() for w in _WORD.findall(_names(e).replace("_", " "))} for e in eps]
    common = set.intersection(*per) if per else set()
    return [w for w in STATUS_WORDS if w in common]


def _uid(e: dict) -> str:
    return str(e.get("uid") or "")


def fix_titles(ds: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Returns (datasets, {new dataset id: dataset id it was split from}) so tags can follow.

    - Every endpoint carries a status word the title lacks: the word is added to the title.
    - Some do and some don't (a live and a removed service grouped under one title, as NSTA's pipeline layers were):
      the dataset is split. The part holding the original id keeps it; the other part takes its first endpoint's id.
      The status part gets the word in its title.
    """
    if "endpoints" not in ds.columns or "title" not in ds.columns:
        return ds, {}
    renamed, splits = 0, {}
    rows, extra = ds.to_dict("records"), []
    for r in rows:
        eps_s = r.get("endpoints")
        if not isinstance(eps_s, str) or not _WORD.search(eps_s):
            continue
        try:
            eps = json.loads(eps_s)
        except Exception:
            continue
        title = str(r.get("title") or "")
        words = [{w.lower() for w in _WORD.findall(_names(e).replace("_", " "))} - {w for w in STATUS_WORDS if re.search(rf"(?<![a-z]){w}", title, re.I)} for e in eps]
        flagged = [e for e, w in zip(eps, words) if w]
        if not flagged:
            continue
        add = [w for w in STATUS_WORDS if w in set.intersection(*[w for w in words if w])]
        label = f"{title} – {', '.join(add) or 'status in service name'}"
        if len(flagged) == len(eps):
            r["title"] = label
            renamed += 1
            continue
        plain = [e for e in eps if e not in flagged]
        orig = r["dataset_id"]
        keep_flagged = any(_uid(e) == orig for e in flagged)
        other = dict(r)
        if keep_flagged:
            r.update(title=label, endpoints=json.dumps(flagged, separators=(",", ":")))
            other.update(dataset_id=_uid(plain[0]) or f"{orig}-live", endpoints=json.dumps(plain, separators=(",", ":")))
        else:
            r.update(endpoints=json.dumps(plain, separators=(",", ":")))
            other.update(dataset_id=_uid(flagged[0]) or f"{orig}-{add[0] if add else 'status'}", title=label,
                         endpoints=json.dumps(flagged, separators=(",", ":")))
        for x, n in ((r, len(json.loads(r["endpoints"]))), (other, len(json.loads(other["endpoints"])))):
            if "n_endpoints" in x:
                x["n_endpoints"] = n
            if "protocols" in x:
                x["protocols"] = sorted({e["protocol"] for e in json.loads(x["endpoints"])})
        splits[other["dataset_id"]] = orig
        extra.append(other)
    out = pd.DataFrame(rows + extra, columns=ds.columns)
    if hasattr(ds, "geometry") and "geometry" in ds.columns:
        import geopandas as gpd
        out = gpd.GeoDataFrame(out, geometry="geometry", crs=ds.crs)
    print(f"titles: {renamed:,} datasets given a status word from their service name; {len(splits):,} split where live and "
          f"{'/'.join(STATUS_WORDS[:3])}… services had been grouped together", flush=True)
    return out, splits
