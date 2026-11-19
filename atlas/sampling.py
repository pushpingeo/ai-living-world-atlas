"""Capability "sample": the endpoint returns a number at a point (a depth in metres, a density), not a picture.
Applied at publish time (combine.py); rules and hand-checked layers in vocab/sample_rules.yaml.

Each sampled endpoint gets "sample" in its capabilities and a "sample" object in its info, which says how to read
the value: method (identify | feature-info | wcs | opendap | lerc-tile), what the value is, and units where known.
Curated records (vocab/seeds/values.yaml) carry their own "sample" info and are left as they are.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

import pandas as pd
import yaml

RULES = Path(__file__).resolve().parent.parent / "vocab" / "sample_rules.yaml"
VALUE_BY_TYPE = {"elevation": "elevation", "thematic": "class"}


@lru_cache
def rules():
    r = yaml.safe_load(RULES.read_text()) or {}
    return re.compile(r.get("never") or r"(?!x)x"), [
        {**f, "_layers": re.compile(f["layers"])} for f in (r.get("feature_info") or [])]


def sample_info(e: dict, title: str) -> dict | None:
    """How to sample this endpoint, or None if it doesn't return values (or we can't tell)."""
    never, fi = rules()
    if never.search(f"{title} {e.get('layer_name') or ''} {e.get('url') or ''}"):
        return None
    info = json.loads(e.get("info") or "{}") if isinstance(e.get("info"), str) else (e.get("info") or {})
    p = e.get("protocol")
    if p == "arcgis-imageserver":
        if info.get("tiles_only") or info.get("bands") != 1 or info.get("data_type") in ("rgb", "processed"):
            return None
        return {"method": "identify", "value": VALUE_BY_TYPE.get(info.get("data_type"), "measure")}
    if p == "wcs":
        return {"method": "wcs", "value": "measure"}
    if p == "wms" and "feature-info" in (e.get("capabilities") or []):
        host = urlsplit(e.get("service_url") or e.get("url") or "").netloc.lower()
        for f in fi:
            if host == f["service"] and f["_layers"].search(e.get("layer_name") or ""):
                return {"method": "feature-info", **{k: f[k] for k in ("field", "value", "units", "vertical_datum", "note") if f.get(k)}}
    return None


def add_sample(ds: pd.DataFrame) -> pd.DataFrame:
    if "endpoints" not in ds.columns:
        return ds
    eps_out, caps_out, n_eps, n_ds = [], [], 0, 0
    for eps_json, caps, title in zip(ds["endpoints"], ds["capabilities"], ds["title"]):
        eps = json.loads(eps_json or "[]")
        changed = False
        for e in eps:
            info = json.loads(e.get("info") or "{}")
            if "sample" in (e.get("capabilities") or []):
                continue  # a curated record that says how to sample itself
            s = sample_info(e, title or "")
            if s:
                info["sample"] = s
                e["info"] = json.dumps(info, separators=(",", ":"))
                e["capabilities"] = list(e.get("capabilities") or []) + ["sample"]
                changed = True
                n_eps += 1
        if changed:
            n_ds += 1
            eps_out.append(json.dumps(eps, separators=(",", ":")))
            caps_out.append(sorted(set(list(caps if caps is not None else [])) | {"sample"}))
        else:
            eps_out.append(eps_json)  # untouched rows stay byte-identical, so the MCP deploy sees no change
            caps_out.append(caps)
    print(f"sampling: {n_eps:,} endpoints on {n_ds:,} datasets return values at a point", flush=True)
    return ds.assign(endpoints=eps_out, capabilities=caps_out)
