"""Publisher registry: who a dataset really comes from, and whether it's trusted (design: docs/publisher-registry-design.md).

vocab/publishers.yaml is reviewed by Rob. A dataset matches an entry in one of three ways, strongest first:

  hosts       the publisher's own servers (subdomains included): bgs.ac.uk
  agol_orgs   the publisher's own ArcGIS Online organisation: NSTA's OZMfUznmLTnWccBc
  hosted      an arrangement with a partner's organisation or platform, which needs BOTH the partner's org (or host)
              AND one of the publisher's credit strings: OS Open Data on Esri UK's organisation, Natural England on
              the Defra group organisation. The partner's own layers (Esri UK's COVID copies) don't match.

All three make a dataset `trusted` when the entry is trusted. An exact credit-string match (`names`) alone only tidies
the publisher name; it never makes a dataset trusted (an Esri Living Atlas copy crediting NOAA isn't NOAA's service).
Entries with `hosting_only: true` are platforms (Esri UK's org, govConnect...): never credited, never trusted.

Weekly, `python -m atlas.publishers candidates` lists unregistered publishers worth a look, for a GitHub issue with
one checkbox each (.github/workflows/publishers.yml). When Rob closes the issue, `apply` writes the ticked ones into
publishers.yaml and the rest into vocab/publishers_declined.yaml, so they don't come back.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlparse

import yaml

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "vocab" / "publishers.yaml"
DECLINED = ROOT / "vocab" / "publishers_declined.yaml"

AGOL = re.compile(r"https?://(?:services|tiles|vectortileservices|features)[\w-]*\.arcgis\.com/([A-Za-z0-9]{10,20})/", re.I)
TWO_PART = {"gov", "ac", "co", "org", "gouv", "govt", "go", "com", "gob", "gv", "or", "nic", "net", "edu", "mil"}
GOV_DOMAIN = re.compile(r"(\.gov(\.[a-z]{2})?|\.gouv\.fr|\.govt\.nz|\.gc\.ca|\.admin\.ch|europa\.eu|\.gob\.[a-z]{2}|"
                        r"\.go\.[a-z]{2}|\.bund\.de|\.gv\.at|\.government\.[a-z]{2}|\.mil)$", re.I)
AUTH_TYPES = {"central-gov", "public-body", "international", "regional-gov"}
# A rough role from the name, only to sort the candidate list (national agencies first); Rob confirms the role.
ROLE_HINTS = [
    ("geological-survey", r"geolog|geoscience|géolog|geologi|bgs\b|brgm|usgs"),
    ("national-mapping", r"ordnance|topograf|topograph|cartogr|cadast|kataster|landesvermessung|geobasis|kartverk|"
                         r"\bign\b|swisstopo|lantmäteri|maanmittaus|geodata|geodesy|land information|spatial services"),
    ("hydrographic", r"hydrograph|admiralty|\bshom\b"),
    ("met-service", r"meteorolog|met office|weather service|hydrolog"),
    ("environment-agency", r"environment agency|environmental protection|umweltbundesamt|umwelt|ambiente|milieu|"
                           r"environnement|miljø|environment"),
    ("energy-regulator", r"petroleum|oil and gas|energy regulator|transition authority|nsta\b|hydrocarbon|mining|minerals"),
    ("nature-agency", r"natural england|naturescot|jncc|nature|wildlife|biodiversity|parks"),
    ("statistics", r"statisti|census|insee|\bcbs\b|\bons\b"),
    ("international", r"united nations|unep|\bfao\b|\besa\b|copernicus|emodnet|gebco|world bank|european"),
]
NATIONAL_ROLES = {"geological-survey", "national-mapping", "hydrographic", "met-service", "energy-regulator", "statistics"}


def tidy(name: str) -> str:
    return re.sub(r"\s+", " ", (name or "").strip()).casefold()


def regdomain(host: str) -> str:
    p = (host or "").lower().split(".")
    if len(p) > 2 and len(p[-1]) == 2 and p[-2] in TWO_PART:
        return ".".join(p[-3:])
    return ".".join(p[-2:])


def source_of(url: str) -> tuple[str, str]:
    """(kind, key): ("agol", org id) for ArcGIS Online, else ("host", hostname)."""
    m = AGOL.match(url or "")
    if m:
        return "agol", m.group(1)
    return "host", (urlparse(url or "").hostname or "").lower()


def load(path: Path = REGISTRY) -> list[dict]:
    if not path.exists():
        return []
    doc = yaml.safe_load(path.read_text()) or {}
    return doc.get("publishers") or []


class Matcher:
    def __init__(self, entries: list[dict]):
        self.hosts, self.orgs, self.hosted, self.names, self.byid = {}, {}, [], {}, {}
        for e in entries:
            self.byid[e["id"]] = e
            m = e.get("match") or {}
            for h in m.get("hosts") or []:
                self.hosts[h.lower()] = e
            for o in m.get("agol_orgs") or []:
                self.orgs[o] = e
            for hd in m.get("hosted") or []:
                self.hosted.append((hd.get("agol_org"), (hd.get("host") or "").lower(),
                                    [tidy(c) for c in hd.get("credits") or []], hd.get("via"), e))
            for n in m.get("names") or []:
                self.names[tidy(n)] = e

    def _host(self, host: str):
        parts = host.split(".")
        for i in range(len(parts) - 1):
            e = self.hosts.get(".".join(parts[i:]))
            if e:
                return e
        return None

    def match(self, urls: list[str], credit: str) -> dict | None:
        """{"id", "name", "trusted", "how", "hosted_by"?} for the first url that matches, else a name-only match."""
        c = tidy(credit)
        for u in urls:
            kind, key = source_of(u)
            # hosted arrangements first: a partner org also has its own entry (hosting_only), which must not win
            for org, host, credits, via, e in self.hosted:
                on = (kind == "agol" and org == key) or (kind == "host" and host and (key == host or key.endswith("." + host)))
                if on and any(x and x in c for x in credits):
                    return self._out(e, "hosted", via)
            e = self.orgs.get(key) if kind == "agol" else self._host(key)
            if e and not e.get("hosting_only"):
                return self._out(e, "agol_org" if kind == "agol" else "host")
        e = self.names.get(c)
        if e and not e.get("hosting_only"):
            out = self._out(e, "name")
            out["trusted"] = False
            return out
        return None

    def _out(self, e, how, via=None):
        out = {"id": e["id"], "name": e["name"], "trusted": bool(e.get("trusted")), "how": how,
               "type": e.get("type"), "country": e.get("country")}
        if via:
            out["hosted_by"] = self.byid[via]["name"] if via in self.byid else via
        return out


def urls_of(endpoints) -> list[str]:
    try:
        return [x.get("url", "") for x in json.loads(endpoints or "[]")]
    except (TypeError, ValueError):
        return []


# ---------------------------------------------------------------- candidates

def role_hint(name: str) -> str:
    for role, rx in ROLE_HINTS:
        if re.search(rx, name or "", re.I):
            return role
    return ""


def candidates(ds, entries: list[dict], declined: set[str], top: int) -> list[dict]:
    """Unregistered sources ranked for review. A source is a host's registered domain or an ArcGIS Online org; one
    that serves several publishers' credits (a shared or partner org, a hosting platform) becomes a hosting_only
    candidate plus one "hosted" candidate per credit."""
    import pandas as pd

    m = Matcher(entries)
    rows = []
    for r in ds.itertuples(index=False):
        us = urls_of(r.endpoints)
        if not us or m.match(us, r.publisher or "") and m.match(us, r.publisher or "")["how"] != "name":
            continue
        kind, key = source_of(us[0])
        if kind == "agol" and key in m.orgs and not m.orgs[key].get("hosting_only"):
            continue
        # A whole hostname, not its registered domain: wa.gov.au is dozens of agencies, each on its own host
        rows.append({"kind": kind, "key": key, "host": key if kind == "host" else "",
                     "credit": (r.publisher or "").strip(), "ptype": r.publisher_type or "unknown",
                     "country": r.country or "", "lic": bool((r.licence or "").strip()), "desc": bool((r.abstract or "").strip())})
    df = pd.DataFrame(rows)
    if df.empty:
        return []
    out = []
    for (kind, key), g in df.groupby(["kind", "key"]):
        if kind == "host" and (key.endswith("arcgis.com") or key.endswith("arcgisonline.com") or not key):
            continue  # ArcGIS Online without an org id in the URL: nothing to match on
        credits = g.credit.value_counts()
        big = credits[credits >= 5]
        shared = len(big) >= 3 and credits.iloc[0] / len(g) < 0.7
        if shared:
            out.append(cand(kind, key, g, key, hosting_only=True))
            for cr in big.index[:15]:
                out.append(cand(kind, key, g[g.credit == cr], cr, via=key))
        else:
            out.append(cand(kind, key, g, credits.index[0]))
    # The same body on several hosts or orgs (Bayerisches Landesamt für Umwelt on three) is one candidate
    merged = {}
    for c in out:
        k = ("platform:" + c["source"]) if c["hosting_only"] else tidy(c["name"])
        if k in merged:
            m0 = merged[k]
            for mk, mv in c["match"].items():
                m0["match"].setdefault(mk, []).extend(x for x in mv if x not in m0["match"][mk])
            m0["n"] += c["n"]; m0["rank"] = round(max(m0["rank"], c["rank"]) * 1.1, 1)
            m0["sources"].append(c["source"])
            m0["cid"] = hashlib.sha1((m0["cid"] + c["cid"]).encode()).hexdigest()[:10]
        else:
            merged[k] = {**c, "sources": [c["source"]]}
    out = [c for c in merged.values() if c["cid"] not in declined and c["n"] >= 5]
    out.sort(key=lambda c: -c["rank"])
    return out[:top]


def cand(kind, key, g, credit, hosting_only=False, via=None) -> dict:
    n = len(g)
    ptype = g.ptype.mode().iat[0]
    country = g.country.mode().iat[0] if len(g.country.mode()) else ""
    hosts = sorted({h for h in g.host if h})[:5]
    gov = any(GOV_DOMAIN.search(h) for h in hosts) or bool(GOV_DOMAIN.search(key if kind == "host" else ""))
    role = "" if hosting_only else role_hint(credit)
    cid = hashlib.sha1(f"{kind}:{key}:{'' if not via else tidy(credit)}:{hosting_only}".encode()).hexdigest()[:10]
    rank = (min(n, 2000) ** 0.5) * (1 + gov + (ptype in AUTH_TYPES) + 2 * (role in NATIONAL_ROLES) + (role != "")
                                     + g.lic.mean() + 0.5 * g.desc.mean())
    match = {}
    if via:
        match["hosted"] = [{("agol_org" if kind == "agol" else "host"): key, "credits": [credit]}]
    elif kind == "agol":
        match["agol_orgs"] = [key]
    else:
        match["hosts"] = [key]
    variants = [c for c in g.credit.value_counts().index[:4]]
    return {"cid": cid, "kind": "platform" if hosting_only else ("hosted" if via else kind), "source": key, "via": via,
            "name": credit[:120], "n": n, "country": country, "type": ptype, "role": role, "gov_domain": gov,
            "licence_share": round(float(g.lic.mean()), 2), "hosts": hosts, "credits_seen": variants,
            "rank": round(rank, 1), "match": match, "hosting_only": hosting_only}


def slug(name: str, taken: set[str]) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", tidy(name)).strip("-")[:40] or "publisher"
    base, i = s, 2
    while s in taken:
        s, i = f"{base}-{i}", i + 1
    return s


def issue_body(cands: list[dict], week: str) -> str:
    lines = [f"Publisher candidates, week of {week}. Tick the ones to add to the registry (as trusted), then close the issue.",
             "Unticked ones are recorded as declined and won't come back. To correct one (name, not trusted, a "
             "different role), add a comment quoting its code; the atlas chat picks it up.", "",
             "Platform = a host or ArcGIS Online organisation serving several publishers' data (never credited or "
             "trusted itself). Hosted = one publisher's data on a platform, matched by platform AND credit.", ""]
    sections = [("National agencies and international bodies", lambda c: c["role"] in NATIONAL_ROLES or c["role"] == "international"),
                ("Other government and public bodies", lambda c: not c["hosting_only"] and c["kind"] != "hosted" and c["type"] in AUTH_TYPES),
                ("Hosted on a platform (matched by platform and credit)", lambda c: c["kind"] == "hosted"),
                ("Everyone else", lambda c: not c["hosting_only"]),
                ("Platforms (serve several publishers' data; recorded so they're never credited, never trusted)", lambda c: True)]
    done = set()
    for title, keep in sections:
        part = [c for c in cands if c["cid"] not in done and keep(c)]
        if not part:
            continue
        lines += [f"### {title}", ""]
        for c in part:
            done.add(c["cid"])
            srcs = ", ".join(c.get("sources", [c["source"]])[:3]) + (f" +{len(c['sources']) - 3}" if len(c.get("sources", [])) > 3 else "")
            flags = ", ".join(x for x in [c["country"] or "intl", c["type"], c["role"], "gov domain" if c["gov_domain"] else "",
                                           f"licence {int(c['licence_share'] * 100)}%"] if x)
            if c["hosting_only"]:
                eg = "; ".join(x[:40] for x in c["credits_seen"][:3])
                lines.append(f"- [ ] **{c['source']}**: {c['n']} datasets ({flags}), e.g. {eg} `{c['cid']}`")
            else:
                lines.append(f"- [ ] **{c['name'][:80]}**: {srcs}, {c['n']} datasets ({flags}) `{c['cid']}`")
        lines.append("")
    return "\n".join(lines)


def apply(body: str, cands_path: Path, approver: str, day: str) -> tuple[int, int]:
    """Ticked boxes -> publishers.yaml (trusted unless a platform); unticked -> publishers_declined.yaml."""
    cands = {c["cid"]: c for c in json.loads(cands_path.read_text())}
    ticked, unticked = set(), set()
    for line in body.splitlines():
        m = re.match(r"\s*- \[( |x|X)\] .*`([0-9a-f]{10})`\s*$", line)
        if m and m.group(2) in cands:
            (ticked if m.group(1).lower() == "x" else unticked).add(m.group(2))
    doc = yaml.safe_load(REGISTRY.read_text()) if REGISTRY.exists() else None
    doc = doc or {"publishers": []}
    entries = doc["publishers"]
    taken = {e["id"] for e in entries}
    platform_ids = {}  # candidate source -> registry id, so hosted entries can name their platform
    for e in entries:
        for o in (e.get("match") or {}).get("agol_orgs", []) + (e.get("match") or {}).get("hosts", []):
            platform_ids[o] = e["id"]
    order = sorted(ticked, key=lambda k: cands[k]["kind"] != "platform")  # platforms first
    for k in order:
        c = cands[k]
        name = c["source"] if c["hosting_only"] else c["name"]
        e = {"id": slug(name, taken), "name": name, "country": c["country"], "type": c["type"]}
        if c["role"]:
            e["role"] = c["role"]
        if c["hosting_only"]:
            e["hosting_only"] = True
            e["trusted"] = False
        else:
            e["trusted"] = True
        match = json.loads(json.dumps(c["match"]))
        for hd in match.get("hosted", []):
            hd["via"] = platform_ids.get(hd.get("agol_org") or hd.get("host"), hd.get("agol_org") or hd.get("host"))
        if c["kind"] not in ("hosted", "platform"):
            match["names"] = [x for x in c["credits_seen"] if x][:3]
        e["match"] = match
        e["added"] = day
        e["approved_by"] = approver
        e["candidate"] = k
        taken.add(e["id"])
        entries.append(e)
        if c["kind"] == "platform":
            platform_ids[c["source"]] = e["id"]
    REGISTRY.write_text(HEADER + yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=120))
    dec = (yaml.safe_load(DECLINED.read_text()) if DECLINED.exists() else None) or {"declined": []}
    dec["declined"] += [{"candidate": k, "name": cands[k]["name"], "source": cands[k]["source"], "date": day}
                        for k in sorted(unticked)]
    DECLINED.write_text("# Candidates Rob left unticked (atlas/publishers.py apply). They don't come back.\n"
                        + yaml.safe_dump(dec, sort_keys=False, allow_unicode=True, width=120))
    return len(ticked), len(unticked)


HEADER = """# Publisher registry: reviewed by Rob. Design and matching rules: docs/publisher-registry-design.md, atlas/publishers.py.
# Weekly candidates arrive as a GitHub issue; ticked ones are added here by the publishers workflow.
# Hand edits are fine: keep ids stable (Tobler may store them) and never reuse one.
"""


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("candidates")
    c.add_argument("--datasets", required=True)
    c.add_argument("--top", type=int, default=20)
    c.add_argument("--out", required=True, help="candidates.json")
    c.add_argument("--issue", required=True, help="issue body (markdown)")
    c.add_argument("--week", required=True)
    a = sub.add_parser("apply")
    a.add_argument("--body", required=True)
    a.add_argument("--candidates", required=True)
    a.add_argument("--approver", required=True)
    a.add_argument("--day", required=True)
    s = sub.add_parser("stats")
    s.add_argument("--datasets", required=True)
    args = ap.parse_args()
    if args.cmd == "candidates":
        import pandas as pd

        ds = pd.read_parquet(args.datasets, columns=["publisher", "publisher_type", "country", "licence", "abstract", "endpoints"])
        declined = {d["candidate"] for d in ((yaml.safe_load(DECLINED.read_text()) or {}).get("declined") or [])} if DECLINED.exists() else set()
        cs = candidates(ds, load(), declined, args.top)
        Path(args.out).write_text(json.dumps(cs, indent=1, ensure_ascii=False))
        Path(args.issue).write_text(issue_body(cs, args.week))
        print(f"{len(cs)} candidates")
    elif args.cmd == "apply":
        t, u = apply(Path(args.body).read_text(), Path(args.candidates), args.approver, args.day)
        print(f"added {t}, declined {u}")
    else:
        import pandas as pd

        ds = pd.read_parquet(args.datasets, columns=["publisher", "endpoints"])
        m = Matcher(load())
        hits = [m.match(urls_of(e), p or "") for p, e in zip(ds.publisher, ds.endpoints)]
        hows = pd.Series([h["how"] if h else "none" for h in hits]).value_counts()
        print(f"{len(ds)} datasets; trusted {sum(1 for h in hits if h and h['trusted'])}")
        print(hows.to_string())
        print(pd.Series([h["id"] for h in hits if h]).value_counts().head(30).to_string())


if __name__ == "__main__":
    main()
