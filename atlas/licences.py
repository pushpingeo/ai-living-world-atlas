"""Licences we infer rather than read. Applied at publish time (combine.py); the wave files keep what was crawled.

US federal works: work made by US federal employees has no US copyright (17 U.S.C. §105). A US dataset from a
federal publisher (publisher_type central-gov, country US) that states no open licence is marked open, with the
inference spelled out in the licence text. It is skipped when the credit line names a non-federal party, because
§105 doesn't cover contractors', universities' or states' work. Approved by Rob, 17 Nov 2026.
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

US_FEDERAL = ("US federal government work: public domain in the US "
              "(inferred, 17 U.S.C. §105; not stated by the publisher)")
NON_FEDERAL = re.compile(
    r"universit|college|institut(?:e|o)\b|\binc\b|\bllc\b|\bltd\b|corporation|\bcorp\b|associates|consult|"
    r"\bstate of\b|state university|county|\bcity of\b|commonwealth|\btribe|nation\b|foundation|conservancy|"
    r"\bwwf\b|\btnc\b|lab\b|laborator", re.I)
# labs named here are federal ones; "lab" alone above is a non-federal hint unless it's one of these
FEDERAL_LABS = re.compile(r"national (?:renewable energy|energy technology) lab|\bnrel\b|\bnetl\b|\bornl\b|\bpnnl\b|"
                          r"\blanl\b|\bsandia\b|argonne|\bnoaa\b.*lab", re.I)


def recognise(ds: pd.DataFrame) -> pd.DataFrame:
    """Re-read the dataset's licence text with the current rule, so a rule fix reaches every wave without a recrawl.
    Before 25 Nov 2026 the crawl missed licences given as URLs (creativecommons.org/licenses/by/4.0/,
    .../publicdomain/zero/1.0/, dcat-ap.de dl-by-de) and counted CC BY-NC and BY-ND as open.
    Upgrade-only, except where the text names an NC or ND term: a crawled `open_licence` can come from a layer's own
    licence text, which the dataset row doesn't carry, so a dataset text that names nothing open doesn't undo it."""
    from .quality import is_open_licence, names_nc_or_nd
    if not {"licence", "open_licence"} <= set(ds.columns):
        return ds
    lic = ds["licence"].fillna("").astype(str)
    old = ds["open_licence"].fillna(False).astype(bool)
    up = lic.map(is_open_licence) & ~old
    down = old & lic.map(names_nc_or_nd)
    print(f"licences: rule re-read: {int(up.sum()):,} now open; {int(down.sum()):,} no longer open (NC or ND named)",
          flush=True)
    return ds.assign(open_licence=(old | up) & ~down)


def infer(ds: pd.DataFrame) -> pd.DataFrame:
    if not {"publisher_type", "country", "licence", "open_licence"} <= set(ds.columns):
        return ds
    lic = ds["licence"].fillna("").astype(str)
    fed = (ds["publisher_type"] == "central-gov") & (ds["country"] == "US") & ~ds["open_licence"].fillna(False).astype(bool)
    other = lic.str.contains(NON_FEDERAL) & ~lic.str.contains(FEDERAL_LABS)
    m = fed & ~other
    credit = lic[m].str.strip().str.slice(0, 300)
    ds = ds.copy()
    ds.loc[m, "licence"] = US_FEDERAL + credit.map(lambda c: f". Credits: {c}" if c else "")
    ds.loc[m, "open_licence"] = True
    print(f"licences: {int(m.sum()):,} US federal datasets marked open (inferred); "
          f"{int((fed & other).sum()):,} skipped because the credit names a non-federal party", flush=True)
    return ds


OVERRIDES = Path(__file__).resolve().parent.parent / "vocab" / "licence_overrides.yaml"


def overrides(ds: pd.DataFrame) -> pd.DataFrame:
    """Licences, attribution lines and terms recorded by hand (vocab/licence_overrides.yaml). Adds `attribution` and
    `terms` columns (blank where nothing is recorded)."""
    import json
    from urllib.parse import urlsplit

    import yaml

    rules = (yaml.safe_load(OVERRIDES.read_text()) or {}).get("rules") or [] if OVERRIDES.exists() else []
    for r in rules:
        r["_layers"] = re.compile(r["layers"]) if r.get("layers") else None
        r["_url"] = re.compile(r["url"]) if r.get("url") else None
    hosts = {r["host"] for r in rules}
    ds = ds.copy()
    for col in ("attribution", "terms"):
        if col not in ds.columns:
            ds[col] = ""
    lic, opn, att, trm = list(ds["licence"]), list(ds["open_licence"]), list(ds["attribution"]), list(ds["terms"])
    n = 0
    for i, eps_json in enumerate(ds["endpoints"]):
        if not eps_json or not any(h in eps_json for h in hosts):
            continue
        eps = json.loads(eps_json)
        for r in rules:
            hit = any(urlsplit(e.get("service_url") or e.get("url") or "").netloc.lower() == r["host"]
                      and (r["_layers"] is None or r["_layers"].search(e.get("layer_name") or ""))
                      and (r["_url"] is None or r["_url"].search(e.get("url") or "")) for e in eps)
            if not hit:
                continue
            if r.get("licence") and not (r.get("only_if_not_open") and bool(opn[i])):
                lic[i], opn[i] = r["licence"], bool(r.get("open", opn[i]))
            att[i] = r.get("attribution", att[i]) or ""
            trm[i] = r.get("terms", trm[i]) or ""
            n += 1
            break
    print(f"licences: {n:,} datasets given a recorded licence, attribution or terms (vocab/licence_overrides.yaml)", flush=True)
    return ds.assign(licence=lic, open_licence=opn, attribution=att, terms=trm)
