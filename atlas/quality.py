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
    r"open government licen[cs]e|\bOGL\b|creative ?commons|\bCC[- ]?BY\b|\bCC[- ]?0\b|cc-by|odbl|open database licen|"
    r"\bPDDL\b|public ?domain|publiek ?domein|licence ouverte|datenlizenz deutschland|dl-de|"
    r"opendatacommons\.org/licenses/(odbl|by|pddl)|\bODC[- ]BY\b|etalab|dl-(by|zero)-de|data licen[cs]e germany|"
    r"opendefinition\.org/licenses/(cc-zero|cc-by|odc)|namensnennung", re.I)
# Non-commercial and no-derivatives terms make a licence not open, even when it is a Creative Commons one
# (CC BY-NC, CC BY-ND, Datenlizenz "nutzungsbeschränkt"). Checked on the same text, after OPEN_LICENCES.
NOT_OPEN = re.compile(
    r"\bby-nc|\bby-nd|\bnc-nd|\bnc-sa|non-?commercial|noncommercial|no ?deriv|noderivs|\bNC\b(?=[ -]?(?:\d|SA|ND|licen))|"
    r"nutzungsbeschr[aä]nkt|personal,? non-commercial", re.I)


# "for commercial and non-commercial use" grants both: not an NC term
BOTH_USES = re.compile(r"(?:commercial|kommerziell\w*)\s+(?:and|or|und|oder)\s+(?:non|nicht)[- ]?(?:commercial|kommerziell\w*)", re.I)


def names_nc_or_nd(text: str) -> bool:
    return bool(NOT_OPEN.search(BOTH_USES.sub(" ", str(text or ""))))


def is_open_licence(text: str) -> bool:
    """Open per the Open Definition: open licence named (as words or as its URL), and no NC or ND term."""
    t = str(text or "")
    return bool(OPEN_LICENCES.search(t)) and not names_nc_or_nd(t)

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
    for scheme in ("inspire", "datagovuk", "eu_data_theme"):
        for k, code in (v.get(scheme) or {}).items():
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


# National authorities pass without a description (Rob, 18 Nov 2026): a national government or national public body's
# live layer is worth listing even when the publisher wrote nothing about it (ONHYM's and Uganda's petroleum layers).
# Junk flags and failed checks still keep a layer out. Local government is not included.
# A TRIAL for regions where data is scarce: only layers whose country is listed here. Rob's reasoning: for Africa,
# something beats nothing; for the US and Europe, with far more data, it may just add noise. Judge Africa first.
AUTHORITATIVE = {"central-gov", "public-body"}
AUTHORITY_PASS_COUNTRIES = set("""DZ AO BJ BW BF BI CV CM CF TD KM CG CD CI DJ EG GQ ER SZ ET GA GM GH GN GW KE LS LR LY MG
MW ML MR MU MA MZ NA NE NG RW ST SN SC SL SO ZA SS SD TZ TG TN UG ZM ZW""".split())
AUTHORITATIVE_MIN_TOTAL = 45


def tidy_title(title: str) -> str:
    """PETROLEUM_AGREEMENTS_OFFSHORE -> Petroleum agreements offshore; UG_Licence_Areas_2023 -> UG licence areas 2023."""
    t = re.sub(r"^[A-Za-z0-9]+:", "", (title or "").strip())  # workspace prefix
    t = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", t)  # camelCase
    words = [w for w in re.split(r"[_\-.\s]+", t) if w]
    if not words:
        return title
    out = [w if (w.isupper() and len(w) <= 3) or any(ch.isdigit() for ch in w) else w.lower() for w in words]
    out[0] = out[0][:1].upper() + out[0][1:]
    return " ".join(out)


def authority_pass(r: dict) -> dict:
    """Apply the national-authority rule to an already-scored layer row (also used when a wave is remerged)."""
    if r.get("q_pass"):
        return r
    flags = r.get("q_flags")
    flags = list(flags) if flags is not None else []
    if (r.get("publisher_type_resolved") in AUTHORITATIVE and (r.get("country") or "") in AUTHORITY_PASS_COUNTRIES
            and not flags and r.get("check_status") != "fail"
            and (r.get("q_total") or 0) >= AUTHORITATIVE_MIN_TOTAL):
        r["q_pass"] = True
        r["q_pass_rule"] = "national-authority"
        dt = r.get("display_title") or ""
        if r.get("q_title_codelike") or codelike(dt) or (dt.isupper() and len(dt) > 12):
            r["display_title"] = tidy_title(r.get("display_title") or r.get("title") or "")
    return r


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

    licence = 10 if is_open_licence(lic) else 5 if lic.strip() else 0

    flags = [name for rx, name in JUNK_TITLE if rx.search(title)]
    if re.match(r"^(topp|sf|tiger|nurc|cite|it\.geosolutions):", str(row.get("layer_name") or ""), re.I) and "demo-data" not in flags:
        flags.append("demo-data")
    total = authority + metadata + liveness + licence
    passes = total >= 60 and not flags and chk != "fail" and m_abs >= 8 and not codelike(title)
    return authority_pass({
        "q_authority": authority, "q_metadata": metadata, "q_liveness": liveness, "q_licence": licence,
        "q_total": total, "q_flags": flags, "q_pass": passes, "publisher_type_resolved": ptype,
        "display_title": title, "q_open_licence": is_open_licence(lic), "q_abstract_len": len(abstract), "q_title_codelike": codelike(title),
        "q_pass_rule": "bar" if passes else "", "check_status": chk,
    })
