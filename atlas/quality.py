"""Trust score: four visible components, plus junk flags. Plain rules, no AI."""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

import yaml

GOV_DOMAINS = (
    ".gov.uk", ".gov.scot", ".gov.wales", ".llyw.cymru", ".nhs.uk", ".police.uk", ".mod.uk",
    ".gov", ".mil", ".gc.ca", ".gov.au", ".govt.nz", ".europa.eu", ".gov.ie", ".nidirect.gov.uk",
)
ACADEMIC_DOMAINS = (".ac.uk", ".edu", ".ac.nz", ".edu.au")

AUTHORITY = {
    "central-gov": 30, "regional-gov": 30, "local-gov": 27, "international": 27,
    "public-body": 25, "curated-collection": 24, "academic": 20, "civil-society": 12, "business": 8, "unknown": 5,
}

OPEN_LICENCES = re.compile(
    r"open government licen[cs]e|\bOGL\b|creative commons|\bCC[- ]?BY\b|\bCC0\b|cc-by|odbl|open database licen|"
    r"\bPDDL\b|public domain|licence ouverte|datenlizenz deutschland|dl-de", re.I)

JUNK_TITLE = [
    (re.compile(r"\b(test|testing|untitled|temp|tmp|draft|demo|sample|backup|copy of|do not use)\b", re.I), "test-or-draft"),
    (re.compile(r"_WFL1$|_WFL\d*$", re.I), "web-map-artefact"),
    (re.compile(r"(^|_)view$|_public_view", re.I), "view-artefact"),
    (re.compile(r"[0-9a-f]{20,}", re.I), "hex-id"),
    (re.compile(r"^(layer|sheet|export_output|default)[ _]?\d*$", re.I), "default-name"),
    (re.compile(r"^\d+$"), "numeric-name"),
    # sample data that ships with GeoServer and MapServer installs
    (re.compile(r"^(spearfish\b|tasmania\b|north america sample imagery|manhattan \(ny\)|usa population|world rectangle|"
                r"a sample arcgrid|pk50095|states_provinces_shp|tiger_roads|poly_landmarks|giant_polygon)", re.I), "demo-data"),
]


@lru_cache
def theme_vocab():
    p = Path(__file__).resolve().parent.parent / "vocab" / "themes.yaml"
    v = yaml.safe_load(p.read_text())
    lookup = {}
    for code, label in v["iso_topic_categories"].items():
        lookup[code.lower()] = code
        lookup[label.lower()] = code
    for scheme in ("inspire", "datagovuk"):
        for k, code in v[scheme].items():
            lookup[k.lower()] = code
    return lookup


def declared_iso_themes(themes: list[str], keywords: list[str]) -> tuple[list[str], str]:
    """ISO categories the source itself declared (explicit theme fields first, then exact keyword matches)."""
    lk = theme_vocab()
    found, how = [], ""
    for t in themes or []:
        for part in re.split(r"[,;|]", str(t)):
            c = lk.get(part.strip().lower())
            if c and c not in found:
                found.append(c)
                how = how or "theme-field"
    for k in keywords or []:
        c = lk.get(str(k).strip().lower())
        if c and c not in found:
            found.append(c)
            how = how or "keyword"
    return found, how


def host_type(url: str) -> str | None:
    h = urlsplit(url).netloc.lower().split(":")[0]
    if any(h.endswith(d) for d in GOV_DOMAINS):
        return "public-body"
    if any(h.endswith(d) for d in ACADEMIC_DOMAINS):
        return "academic"
    return None


@lru_cache
def _overrides():
    p = Path(__file__).resolve().parent.parent / "vocab" / "publisher_overrides.yaml"
    return yaml.safe_load(p.read_text()) or {} if p.exists() else {}


def publisher_override(url: str) -> str | None:
    h = urlsplit(url).netloc.lower()
    for dom, t in _overrides().items():
        if h == dom or h.endswith("." + dom):
            return t
    return None


def codelike(title: str) -> bool:
    t = (title or "").strip()
    return (not t) or (" " not in t and ("_" in t or t.isupper() or len(t) <= 3))


def score(row: dict) -> dict:
    """row: a layer dict with crawl + check info. Returns score components and flags."""
    ptype = publisher_override(row.get("service_url", "")) or row.get("publisher_type") or "unknown"
    if ptype in ("unknown", "", None):
        ptype = host_type(row.get("service_url", "")) or ("public-body" if (row.get("discovered_via") or "").startswith("ckan:") else "unknown")
    authority = AUTHORITY.get(ptype, 5)

    title = row.get("title") or ""
    if codelike(title) and row.get("portal_title"):
        title = row["portal_title"]  # the catalogue record usually has the human name
    # A service description shared by dozens of layers says nothing about any one of them,
    # so it only counts for small services.
    svc_abs = row.get("service_abstract") or "" if (row.get("service_layer_count") or 1) <= 3 else ""
    abstract = max((row.get("abstract") or "", row.get("portal_abstract") or "", svc_abs), key=len)
    lic = " ".join(x for x in (row.get("licence_text") or "", row.get("portal_licence") or "") if x)
    m_title = 3 if codelike(title) else 8
    m_abs = 12 if len(abstract) >= 200 else 8 if len(abstract) >= 50 else 2 if abstract else 0
    m_kw = 5 if len(row.get("keywords") if row.get("keywords") is not None else []) else 0
    m_lic = 10 if lic.strip() else 0
    m_bbox = 5 if row.get("bbox") else 0
    metadata = m_title + m_abs + m_kw + m_lic + m_bbox

    chk = row.get("check_status") or "unchecked"
    liveness = 10 + {"ok": 10, "empty": 5, "unchecked": 5, "fail": 0}.get(chk, 0)

    licence = 10 if OPEN_LICENCES.search(lic) else 5 if lic.strip() else 0

    flags = [name for rx, name in JUNK_TITLE if rx.search(title)]
    if re.match(r"^(topp|sf|tiger|nurc|cite|it\.geosolutions):", str(row.get("layer_name") or ""), re.I) and "demo-data" not in flags:
        flags.append("demo-data")
    total = authority + metadata + liveness + licence
    passes = total >= 60 and not flags and chk != "fail" and m_abs >= 8 and not codelike(title)
    return {
        "q_authority": authority, "q_metadata": metadata, "q_liveness": liveness, "q_licence": licence,
        "q_total": total, "q_flags": flags, "q_pass": passes, "publisher_type_resolved": ptype,
        "display_title": title, "q_open_licence": bool(OPEN_LICENCES.search(lic)), "q_abstract_len": len(abstract), "q_title_codelike": codelike(title),
    }
