"""Licences we infer rather than read. Applied at publish time (combine.py); the wave files keep what was crawled.

US federal works: work made by US federal employees has no US copyright (17 U.S.C. §105). A US dataset from a
federal publisher (publisher_type central-gov, country US) that states no open licence is marked open, with the
inference spelled out in the licence text. It is skipped when the credit line names a non-federal party, because
§105 doesn't cover contractors', universities' or states' work. Approved by Rob, 17 Nov 2026.
"""
from __future__ import annotations

import re

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
