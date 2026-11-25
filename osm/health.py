"""Nightly health check of the hosted OpenStreetMap copy, run by the sweep workflow.

Prints a markdown section for results/liveness/REPORT.md:
- the bucket's lifecycle rules, read from the Cloudflare API (so the report shows what is actually set);
- per market, how old the live manifest is and the oldest release folder it points into.

Why: the R2 rule "osm-old-releases" deletes objects under osm/20 thirty days after upload (Rob, 25 Nov 2026). A manifest
can point into an older release for up to 14 days (`carried`), then waits up to 7 days for the next weekly run. If weekly
publishing stops, the rule would in time delete files a live manifest still points to. This check warns well before.

Never fails the sweep: every problem becomes a line in the report.
    python3 osm/health.py >> out/REPORT.md
"""
import json
import os
import sys
import urllib.request
from datetime import date, datetime, timezone

BASE = "https://data.asktobler.com/osm/"
BUCKET = "atlas-data"
MANIFEST_WARN_DAYS = 10   # weekly runs: a manifest older than this means a run or two were missed
RELEASE_WARN_DAYS = 23    # the lifecycle rule deletes at 30: warn a week ahead
MARKETS = ("uk", "nl", "au", "us")


def get_json(url, headers=None, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "atlas-osm-health", **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def lifecycle_lines():
    token, account = os.environ.get("CLOUDFLARE_API_TOKEN"), os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    if not token or not account:
        return ["- Lifecycle rules: not checked (no Cloudflare credentials in this run)"]
    url = f"https://api.cloudflare.com/client/v4/accounts/{account}/r2/buckets/{BUCKET}/lifecycle"
    try:
        d = get_json(url, {"Authorization": f"Bearer {token}"})
    except Exception as e:  # noqa: BLE001
        return [f"- Lifecycle rules: **could not be read** ({type(e).__name__}: {e})"]
    rules = (d.get("result") or {}).get("rules") or []
    out = [f"- Lifecycle rules on {BUCKET}: {len(rules)}"]
    found = False
    for r in rules:
        prefix = (r.get("conditions") or {}).get("prefix", "")
        delete = r.get("deleteObjectsTransition") or {}
        cond = delete.get("condition") or {}
        if cond.get("type") == "Age" and cond.get("maxAge"):
            what = f"delete after {int(cond['maxAge']) // 86400} days"
        elif delete:
            what = f"delete: {json.dumps(cond)}"
        elif r.get("abortMultipartUploadsTransition"):
            what = "abort incomplete multipart uploads"
        else:
            what = "other"
        out.append(f"  - `{r.get('id', '?')}`: prefix `{prefix or '(whole bucket)'}`, {what}, "
                   f"{'enabled' if r.get('enabled') else '**disabled**'}")
        if delete and r.get("enabled"):
            if prefix == "osm/20" and cond.get("maxAge") == 30 * 86400:
                found = True
            elif prefix == "" or "osm/".startswith(prefix) or (prefix.startswith("osm/") and not prefix.startswith("osm/20")):
                out.append("    - **Warning: this rule can delete manifests or other live files**")
    if not found:
        out.append("  - **Warning: the expected rule (prefix `osm/20`, delete after 30 days, enabled) was not found**")
    return out


def age_days(iso_day, today):
    return (today - date.fromisoformat(iso_day[:10])).days


def manifest_lines(today):
    out = []
    for m in MARKETS:
        try:
            man = get_json(BASE + f"{m}.json")
        except urllib.error.HTTPError as e:
            out.append(f"- {m}: no manifest" if e.code == 404 else f"- {m}: manifest **could not be read** (HTTP {e.code})")
            continue
        except Exception as e:  # noqa: BLE001
            out.append(f"- {m}: manifest **could not be read** ({type(e).__name__})")
            continue
        built = man.get("built_at") or man.get("release") or ""
        releases = set()
        for reg in man.get("regions") or man.get("extracts") or []:
            for f in (reg.get("files") or {}).values():
                p = f.get("path", "") if isinstance(f, dict) else ""
                if p[:4].isdigit():
                    releases.add(p.split("/", 1)[0])
        oldest = min(releases) if releases else man.get("release")
        line = f"- {m}: release {man.get('release', '?')}"
        warn = []
        if built:
            a = age_days(built, today)
            line += f", manifest {a} days old"
            if a > MANIFEST_WARN_DAYS:
                warn.append(f"manifest older than {MANIFEST_WARN_DAYS} days: is the weekly run working?")
        if oldest:
            a = age_days(oldest, today)
            line += f", oldest release pointed to {oldest} ({a} days)"
            if a > RELEASE_WARN_DAYS:
                warn.append(f"files it points to are deleted by the lifecycle rule at 30 days")
        if man.get("carried"):
            line += f", {len(man['carried'])} carried"
        out.append(line + "".join(f" **Warning: {w}**" for w in warn))
    return out


def main():
    today = datetime.now(timezone.utc).date()
    lines = ["", "## Hosted OpenStreetMap copy", ""] + lifecycle_lines() + manifest_lines(today)
    print("\n".join(lines))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        print(f"\n## Hosted OpenStreetMap copy\n\n- Check failed: {type(e).__name__}: {e}")
    sys.exit(0)
