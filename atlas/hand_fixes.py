"""Hand fixes applied at publish time by combine.py; the wave and tag files keep what was crawled and tagged.
- apply: concepts set by hand over the AI tags (vocab/concept_overrides.yaml)
- publisher_types: publisher types set by publisher name (vocab/publisher_type_overrides.yaml), for publishers whose
  host is shared (ArcGIS Online) so vocab/publisher_overrides.yaml (by host, at crawl time) can't reach them."""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import yaml

RULES = Path(__file__).resolve().parent.parent / "vocab" / "concept_overrides.yaml"


def apply(tags: pd.DataFrame, ds: pd.DataFrame, path: Path = RULES) -> pd.DataFrame:
    if not path.exists() or tags.empty:
        return tags
    rules = (yaml.safe_load(path.read_text()) or {}).get("rules") or []
    meta = ds[["dataset_id", "title", "publisher"]].fillna("")
    hits: dict[str, list] = {}
    for r in rules:
        m = r.get("match") or {}
        sel = pd.Series(True, index=meta.index)
        if m.get("ids"):
            sel &= meta["dataset_id"].isin(m["ids"])
        for col in ("publisher", "title"):
            if m.get(col):
                sel &= meta[col].str.contains(m[col], flags=re.I, regex=True)
            if m.get(f"not_{col}"):
                sel &= ~meta[col].str.contains(m[f"not_{col}"], flags=re.I, regex=True)
        if not (m.get("ids") or m.get("publisher") or m.get("title")):
            continue  # a rule that matches nothing specific would rewrite everything
        for did in meta.loc[sel, "dataset_id"]:
            hits[did] = list(r["set"])
    if not hits:
        return tags
    tags = tags.copy()
    on = tags["dataset_id"].isin(hits.keys())
    tags.loc[on, "concepts"] = pd.Series([hits[d] for d in tags.loc[on, "dataset_id"]], index=tags.index[on], dtype=object)
    if "reason" in tags.columns:
        tags.loc[on, "reason"] = tags.loc[on, "reason"].fillna("").astype(str) + " [concepts set by hand: vocab/concept_overrides.yaml]"
    print(f"concepts: {int(on.sum())} datasets given hand-set concepts (vocab/concept_overrides.yaml)")
    return tags


PTYPES = Path(__file__).resolve().parent.parent / "vocab" / "publisher_type_overrides.yaml"


def publisher_types(ds: pd.DataFrame, path: Path = PTYPES) -> pd.DataFrame:
    if not path.exists():
        return ds
    rules = (yaml.safe_load(path.read_text()) or {}).get("rules") or []
    pub = ds["publisher"].fillna("")
    types = ds["publisher_type"].copy()
    n = 0
    for r in rules:
        sel = pub.str.contains(r["publisher"], flags=re.I, regex=True) & (types != r["type"])
        types[sel] = r["type"]
        n += int(sel.sum())
    print(f"publisher types: {n} datasets given a hand-set publisher type (vocab/publisher_type_overrides.yaml)")
    return ds.assign(publisher_type=types)
