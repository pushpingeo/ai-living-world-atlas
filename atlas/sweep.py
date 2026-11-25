"""Rolling liveness sweep: recheck published services on a schedule, cheaply.

python -m atlas.sweep --datasets pub/datasets.parquet --layers pub/layers.parquet --state prev/state.parquet --out out

One unit of work is a service (an ArcGIS service, or an OGC server for one protocol). Each check costs what a crawl
of that service costs: one or two metadata requests (service JSON + /layers, or GetCapabilities), plus one small
data request for one of its layers, rotating week by week. From that one visit we learn, for every published
endpoint on the service:
  - does the service still resolve, and is the layer still listed in it;
  - has the publisher changed the layer's title or description (so its dataset can be re-tagged);
  - for the one sampled layer, does it still return data.

Schedule (all in days): a resolving service is due every 7, a failing one every 3, a retired one every 28.
An endpoint is retired after failing on 3 checks spanning at least 14 days (30 when its whole host was down,
which can also be a block on our runner rather than a dead server). A retired endpoint that resolves again
comes back. Robots.txt refusals don't count as failures.

Outputs: state.parquet (one row per endpoint), changes.parquet (current title/description overrides),
retag.parquet (datasets whose text changed this run, ready for tag_batch), REPORT.md and history.csv.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import random
import time
from collections import Counter, defaultdict
from datetime import date, timedelta
from itertools import zip_longest
from pathlib import Path
from urllib.parse import urlsplit

import pandas as pd

from . import crawl_arcgis, crawl_ogc
from .net import Client

DUE_OK, DUE_FAIL, DUE_RETIRED = 7, 3, 28
RETIRE_CHECKS, RETIRE_DAYS, RETIRE_DAYS_HOST = 3, 14, 30
HOST_DOWN_MIN, HOST_DOWN_SHARE = 20, 0.8   # a host is "down" when 80%+ of 20+ services checked on it failed
# second look at the end of a run: up to 3,000 failed services (40 per host), one at a time per host, 90 s timeout,
# with the last 20 minutes of the run kept for it
SECOND_LOOK_MAX, SECOND_LOOK_PER_HOST, SECOND_LOOK_TIMEOUT, SECOND_LOOK_RESERVE = 3000, 40, 90, 20
FIRST_PASS_SLOTS = 256                     # services in progress at once in the first pass (see run_checks)
FIRST_PASS_GRACE = 120                     # seconds a service already started may run past the first pass's end before it is cut
HOST_GIVE_UP = 10                          # stop knocking on a host after this many network failures in a row
OGC = {"wms": "WMS", "wfs": "WFS", "wmts": "WMTS", "wcs": "WCS"}
PLAIN = {"download", "cloud", "api", "landing", "geojson", "opendap", "ogc-api-features"}  # geojson: atlas-hosted tiles, checked via index.json; opendap: GET of its .dds; ogc-api-features: GET of the collection
RESOLVING = {"ok", "unmatched"}
FAILING = {"fail", "missing", "host-down"}

STATE_COLS = ["uid", "dataset_id", "service_url", "protocol", "status", "detail", "last_checked", "last_ok",
              "fails_in_row", "first_fail", "retired", "retired_at", "data_check", "data_checked",
              "data_detail", "cur_title", "cur_abstract", "text_changed", "text_seen", "title_from_service",
              "abstract_from_service"]


def _norm(s) -> str:
    return " ".join(str(s or "").split())


def population(datasets: str, layers: str) -> pd.DataFrame:
    """Every published endpoint with the title/description it was published with."""
    ds = pd.read_parquet(datasets, columns=["dataset_id", "endpoints"])
    rows = []
    for did, eps in zip(ds["dataset_id"], ds["endpoints"]):
        for e in json.loads(eps):
            if "manual_check" in (e.get("info") or ""):
                continue  # a curated record whose host refuses GitHub's runners; checked by hand (atlas/records.py)
            rows.append((e["uid"], did, e.get("service_url") or e["url"], e["protocol"]))
    pop = pd.DataFrame(rows, columns=["uid", "dataset_id", "service_url", "protocol"]).drop_duplicates("uid")
    cols = ["uid", "title", "abstract"]
    ly = pd.read_parquet(layers, columns=cols).drop_duplicates("uid")
    pop = pop.merge(ly.rename(columns={"title": "orig_title", "abstract": "orig_abstract"}), on="uid", how="left")
    return pop


def load_state(path: str | None) -> pd.DataFrame:
    if path and Path(path).exists() and Path(path).stat().st_size:
        st = pd.read_parquet(path)
        if "text_seen" not in st.columns:  # first-version state compared against crawl text: drop those changes
            st["cur_title"], st["cur_abstract"] = None, None
        for c in STATE_COLS:
            if c not in st.columns:
                st[c] = None
        return st[STATE_COLS]
    return pd.DataFrame(columns=STATE_COLS)


def due_services(pop: pd.DataFrame, st: pd.DataFrame, today: date, cap: int, seed: int) -> list[tuple[str, str]]:
    """Which services to check today, most urgent first, at most `cap`."""
    m = pop[["uid", "service_url", "protocol"]].merge(
        st[["uid", "last_checked", "fails_in_row", "retired"]], on="uid", how="left")
    m["retired"] = m["retired"].fillna(False).astype(bool)
    m["fails_in_row"] = m["fails_in_row"].fillna(0).astype(int)
    g = m.groupby(["service_url", "protocol"]).agg(
        last=("last_checked", lambda s: min((x for x in s if isinstance(x, str) and x), default="")),
        failing=("fails_in_row", "max"), retired=("retired", "all")).reset_index()
    t = today.isoformat()

    def age(d):
        return 10_000 if not d else (today - date.fromisoformat(d)).days

    g["age"] = g["last"].map(age)
    g["urgency"] = 3  # 0 = failing, 1 = never checked, 2 = routine, 3 = not due
    g.loc[(g["failing"] > 0) & ~g["retired"] & (g["age"] >= DUE_FAIL), "urgency"] = 0
    g.loc[g["last"] == "", "urgency"] = 1
    g.loc[(g["urgency"] == 3) & ~g["retired"] & (g["failing"] == 0) & (g["age"] >= DUE_OK), "urgency"] = 2
    g.loc[(g["urgency"] == 3) & g["retired"] & (g["age"] >= DUE_RETIRED), "urgency"] = 2
    g = g[g["urgency"] < 3]
    # never-checked services in random order, so the first runs sample every host rather than draining one
    g["r"] = [random.Random(f"{seed}{t}{u}").random() for u in g["service_url"]]
    g = g.sort_values(["urgency", "age", "r"], ascending=[True, False, True]).head(cap)
    return list(zip(g["service_url"], g["protocol"]))


async def check_service(c: Client, svc: str, proto: str):
    """Returns (status, detail, layers, network_failure). status: ok | fail | robots."""
    if proto.startswith("arcgis-"):
        layers, s = await crawl_arcgis.crawl_service(c, svc, {})
    elif proto in OGC:
        layers, s = await crawl_ogc.crawl_ogc(c, svc, OGC[proto], {})
    elif proto in PLAIN:
        u = urlsplit(svc)
        if u.netloc.endswith(".amazonaws.com") and u.path.endswith("/") and "s3" in u.netloc and not u.query:
            # an S3 "folder" (e.g. Overture's /release/) has no object behind it and answers 404: list it instead
            prefix = u.path.lstrip("/")
            r = await c.get(f"{u.scheme}://{u.netloc}/?list-type=2&max-keys=1&delimiter=/&prefix={prefix}", retries=1)
            if r.ok and b"<Contents>" not in r.body and b"<CommonPrefixes>" not in r.body:
                r = type(r)(r.url, 404, r.ms, error="S3 prefix is empty")
        else:
            r = await c.get(svc, retries=1)
        s = {"ok": r.ok, "error": r.error or ("" if r.ok else f"HTTP {r.status}")}
        layers = []
    else:
        return "unchecked", f"protocol {proto} not checked", [], False
    err = s.get("error") or ""
    if s.get("ok"):
        return "ok", f"{len(layers)} layers", layers, False
    if "robots.txt" in err:
        return "robots", err, [], False
    net = not err.startswith("HTTP") and not err.startswith("parse") and err not in ("not json",)
    return "fail", err[:160], [], net


async def run_checks(services, deadline: float, week: int, data_checks: bool = True):
    results = {}
    host_net_fails: Counter = Counter()
    stats = Counter()

    # A service waits for a slot before it looks at the clock. gather() starts every task at once, so a clock check at
    # the top of a task passes for all of them at minute zero and the deadline never bites (24 Nov ran 307 minutes on a
    # 240-minute budget). Slots are wider than the client's 64 connections so a few slow hosts can't starve the rest.
    # A service still waiting on a slow host when time runs out is cancelled at `hard` and records nothing, so it
    # stays due and is first in line tomorrow.
    async def one(c, gate, svc, proto, until, hard, second=False):
        async with gate:
            if time.monotonic() > until:
                return
            try:
                async with asyncio.timeout(max(1.0, hard - time.monotonic())):
                    await _one(c, svc, proto, until, second)
            except TimeoutError:
                stats["cut_at_deadline"] += 1

    async def _one(c, svc, proto, until, second=False):
            host = urlsplit(svc).netloc
            if time.monotonic() > until:
                return
            if not second and host_net_fails[host] >= HOST_GIVE_UP:
                results[(svc, proto)] = ("fail", "host unreachable (stopped after repeated network failures)", [], True, None)
                return
            try:
                status, detail, layers, net = await check_service(c, svc, proto)
            except Exception as e:  # one odd service must not stop the sweep
                status, detail, layers, net = "fail", f"{type(e).__name__}: {e}"[:160], [], False
            host_net_fails[host] = host_net_fails[host] + 1 if net else 0
            data = None
            if status == "ok" and layers and data_checks and time.monotonic() < until:
                L = layers[week % len(layers)]
                fn = crawl_ogc.check_layer if L.service_type in OGC else crawl_arcgis.check_layer
                try:
                    data = (L.uid, *(await fn(c, L)))
                except Exception as e:
                    data = (L.uid, "fail", type(e).__name__)
            if second and status != "ok":
                return  # keep the first pass's result and detail
            results[(svc, proto)] = (status, detail, layers, net, data)

    async with Client(total=64, per_host=2, timeout=30) as c:
        # spread hosts out so a slow host with thousands of services doesn't hold the queue
        # leave the last few minutes for the second look; services not reached are first in line tomorrow
        first_until = deadline - min(SECOND_LOOK_RESERVE * 60, (deadline - time.monotonic()) / 6)
        gate = asyncio.Semaphore(FIRST_PASS_SLOTS)
        await asyncio.gather(*[one(c, gate, s, p, first_until, first_until + FIRST_PASS_GRACE) for s, p in services])
        stats.update(c.stats)
    # Second look at failures, one at a time per host and with a long timeout. Some live services are just slow
    # (a 3.7 MB WFS GetCapabilities taking 47 s; dados.gov.pt redirects taking 40-60 s) and would otherwise fail
    # every visit and be retired; others refuse or time out only when we arrive alongside other requests.
    per_host: Counter = Counter()
    again = []
    for k, v in results.items():
        h = urlsplit(k[0]).netloc
        if v[0] == "fail" and per_host[h] < SECOND_LOOK_PER_HOST and len(again) < SECOND_LOOK_MAX:
            per_host[h] += 1
            again.append(k)
    if again and time.monotonic() < deadline:
        async with Client(total=16, per_host=1, timeout=SECOND_LOOK_TIMEOUT) as c:
            before = sum(results[k][0] == "ok" for k in again)
            # stop starting retries 3 minutes early: one in flight can take 2 x 90 s (18 Nov ran 4.5 min over)
            # one slot per connection, hosts interleaved, so the 3-minute stop isn't overrun by retries queued on one host
            by_host = defaultdict(list)
            for k in again:
                by_host[urlsplit(k[0]).netloc].append(k)
            order = [k for grp in zip_longest(*by_host.values()) for k in grp if k is not None]
            gate = asyncio.Semaphore(16)
            await asyncio.gather(*[one(c, gate, s, p, deadline - 180, deadline, second=True) for s, p in order])
            stats.update(c.stats)
            stats["second_look"] = len(again)
            stats["second_look_ok"] = sum(results[k][0] == "ok" for k in again) - before
        print(f"second look: {stats['second_look_ok']:,} of {len(again):,} failed services answered", flush=True)
    if stats["cut_at_deadline"]:
        print(f"{stats['cut_at_deadline']:,} services cut off at the deadline (left due for tomorrow)", flush=True)
    return results, dict(stats)


def apply(pop: pd.DataFrame, st: pd.DataFrame, results: dict, today: date):
    """Fold today's results into the per-endpoint state. Returns (state, today's per-endpoint outcomes, retag ids)."""
    t = today.isoformat()
    st = pop[["uid", "dataset_id", "service_url", "protocol", "orig_title", "orig_abstract"]].merge(
        st.drop(columns=["dataset_id", "service_url", "protocol"]), on="uid", how="left")
    for col in ("status", "detail", "last_checked", "last_ok", "first_fail", "retired_at", "data_check", "data_detail",
                "data_checked", "cur_title", "cur_abstract", "text_changed", "orig_title", "orig_abstract", "text_seen",
                "title_from_service", "abstract_from_service"):
        st[col] = st[col].astype(object).where(st[col].notna(), None)  # NaN from the merge -> None
    st["retired"] = st["retired"].fillna(False).astype(bool)
    st["fails_in_row"] = st["fails_in_row"].fillna(0).astype(int)

    # host-level outage: most of a host's checked services failed today
    by_host = defaultdict(lambda: [0, 0])
    for (svc, _), (status, *_r) in results.items():
        if status in ("ok", "fail"):
            h = by_host[urlsplit(svc).netloc]
            h[0] += 1
            h[1] += status == "fail"
    down = {h for h, (n, f) in by_host.items() if n >= HOST_DOWN_MIN and f / n >= HOST_DOWN_SHARE}

    found: dict[str, object] = {}
    svc_matched: Counter = Counter()
    svc_returned: Counter = Counter()
    data_by_uid = {}
    for (svc, proto), (status, detail, layers, net, data) in results.items():
        svc_returned[(svc, proto)] = len(layers)
        for L in layers:
            found[L.uid] = L
        if data:
            data_by_uid[data[0]] = (data[1], data[2])
    known = st.groupby(["service_url", "protocol"])["uid"].apply(list).to_dict()
    for k, uids in known.items():
        svc_matched[k] = sum(u in found for u in uids)

    retag, outcomes = set(), []
    rec = st.to_dict("records")
    for r in rec:
        k = (r["service_url"], r["protocol"])
        if k not in results:
            continue
        status, detail = results[k][0], results[k][1]
        if status in ("robots", "unchecked"):
            r.update(status=status, detail=detail, last_checked=t)
            outcomes.append((r["uid"], status))
            continue
        if status == "ok":
            if r["protocol"] in PLAIN:
                s = "ok"
            elif r["uid"] in found:
                s = "ok"
            elif svc_matched[k] > 0 or svc_returned[k] == 0:
                s, detail = "missing", "layer no longer listed in the service"
            else:
                # the service answers but none of its known layers match: most likely a parsing difference or a
                # restructure we can't attribute, so don't count it against the endpoint
                s, detail = "unmatched", "service resolves; layer ids no longer match"
        else:
            s = "host-down" if urlsplit(r["service_url"]).netloc in down else "fail"
        r["status"], r["detail"], r["last_checked"] = s, detail, t
        if s in RESOLVING:
            if r["retired"]:
                r["detail"] = "revived: " + str(r["detail"])
            r.update(fails_in_row=0, first_fail=None, last_ok=t, retired=False, retired_at=None)
        else:
            r["fails_in_row"] = int(r["fails_in_row"]) + 1
            r["first_fail"] = r["first_fail"] or t
            span = (today - date.fromisoformat(r["first_fail"])).days
            need = RETIRE_DAYS_HOST if s == "host-down" else RETIRE_DAYS
            if not r["retired"] and r["fails_in_row"] >= RETIRE_CHECKS and span >= need:
                r["retired"], r["retired_at"] = True, t
        if r["uid"] in data_by_uid:
            r["data_check"], r["data_detail"], r["data_checked"] = data_by_uid[r["uid"]][0], str(data_by_uid[r["uid"]][1])[:120], t
        # publisher edits to the title or description. The first visit records a baseline of what the service
        # says (the crawl's stored text can differ for reasons that aren't edits: a catalogue title used in its
        # place, accents stripped by a server, parser changes). Later visits compare against that baseline.
        # A change is carried only for the parts whose stored text came from the service, because those are the
        # only ones it makes sense to replace.
        L = found.get(r["uid"])
        if L is not None:
            nt, na = _norm(L.title), _norm(L.abstract)
            h = hashlib.sha1(f"{nt}\x1f{na}".encode()).hexdigest()[:16]
            if r.get("text_seen") is None:
                r["text_seen"] = h
                r["title_from_service"] = nt == _norm(r.get("orig_title"))
                r["abstract_from_service"] = na == _norm(r.get("orig_abstract"))
                r.update(cur_title=None, cur_abstract=None)
            elif h != r["text_seen"]:
                r["text_seen"], r["text_changed"] = h, t
                ct = L.title if r.get("title_from_service") and nt != _norm(r.get("orig_title")) else None
                ca = L.abstract if r.get("abstract_from_service") and na != _norm(r.get("orig_abstract")) else None
                r.update(cur_title=ct, cur_abstract=ca)
                retag.add(r["dataset_id"])
        outcomes.append((r["uid"], r["status"]))
    st = pd.DataFrame(rec)
    return st, outcomes, retag, down


def patched_datasets(datasets: str, changes: pd.DataFrame, ids: set | None = None) -> pd.DataFrame:
    """Datasets with publisher text edits applied. A dataset's title/description is replaced only where it is the
    layer's original text (a catalogue record's wording, used in preference, is left alone)."""
    import geopandas as gpd

    if not len(changes):
        return gpd.GeoDataFrame()
    want = set(changes["dataset_id"]) if ids is None else ids
    ds = gpd.read_parquet(datasets, filters=[("dataset_id", "in", list(want))])
    ch = changes[changes["dataset_id"].isin(want)]
    by = {}
    for r in ch.to_dict("records"):
        by.setdefault(r["dataset_id"], []).append(r)
    titles, abstracts, hit = [], [], []
    for did, t0, a0 in zip(ds["dataset_id"], ds["title"], ds["abstract"]):
        t1, a1, h = t0, a0, False
        for c in by.get(did, []):
            if c.get("cur_title") and _norm(t0) == _norm(c["orig_title"]):
                t1 = c["cur_title"]
            if c.get("cur_abstract") is not None and _norm(a0) == _norm(c["orig_abstract"]):
                a1 = c["cur_abstract"]
        h = _norm(t1) != _norm(t0) or _norm(a1) != _norm(a0)
        titles.append(t1), abstracts.append(a1), hit.append(h)
    ds = ds.assign(title=titles, abstract=abstracts)
    return ds[hit]


def report(st: pd.DataFrame, outcomes, results, down, retag_n, retag_note, today, secs, stats, n_due) -> tuple[str, dict]:
    oc = Counter(s for _, s in outcomes)
    checked = st[st["last_checked"].notna() & (st["last_checked"] != "")]
    live = checked[~checked["retired"]]
    res_rate = lambda d: round(d["status"].isin(RESOLVING).mean(), 4) if len(d) else None  # noqa: E731
    svc_today = Counter(v[0] for v in results.values())
    newly = int((st["retired_at"] == today.isoformat()).sum())
    revived = int(st["detail"].astype(str).str.startswith("revived").sum() if len(st) else 0)
    by_proto = live.groupby("protocol")["status"].apply(lambda s: round(s.isin(RESOLVING).mean(), 3)).to_dict()
    dc = st["data_check"].value_counts().to_dict()
    h = {
        "date": today.isoformat(), "services_due": n_due, "services_checked": sum(svc_today.values()),
        "endpoints_checked_today": len(outcomes), "endpoints_total": len(st),
        "endpoints_ever_checked": len(checked), "resolving_rate": res_rate(live),
        "retired_total": int(st["retired"].sum()), "retired_today": newly, "revived_today": revived,
        "text_changes_today": retag_n, "requests": stats.get("requests", 0), "minutes": round(secs / 60, 1),
        "second_look": stats.get("second_look", 0), "second_look_ok": stats.get("second_look_ok", 0),
    }
    fails = live[live["status"].isin(FAILING)]
    top = fails["service_url"].map(lambda u: urlsplit(u).netloc).value_counts().head(15)
    lines = [
        f"# Liveness sweep {today.isoformat()}", "",
        f"- Services checked today: {h['services_checked']:,} of {n_due:,} due ({h['minutes']} min, {h['requests']:,} requests)",
        *([f"- Stopped at the time limit: {stats['cut_at_deadline']:,} services were cut off mid-check and stay due"]
          if stats.get("cut_at_deadline") else []),
        f"- Service results today: " + ", ".join(f"{k} {v:,}" for k, v in svc_today.most_common()),
        f"- Endpoints checked today: {len(outcomes):,}: " + ", ".join(f"{k} {v:,}" for k, v in oc.most_common()),
        f"- Second look (slow retry of failed services): {h['second_look_ok']:,} of {h['second_look']:,} answered",
        "",
        f"- Published endpoints: {len(st):,}; checked at least once: {len(checked):,} ({len(checked) / max(len(st), 1):.0%})",
        f"- **Resolving at last check: {h['resolving_rate']:.1%}** of checked endpoints that aren't retired (target 98%)" if h["resolving_rate"] is not None else "- Resolving: nothing checked yet",
        f"- By protocol: " + ", ".join(f"{k} {v:.1%}" for k, v in sorted(by_proto.items())),
        f"- Data checks on record (one sampled layer per service per visit): " + ", ".join(f"{k} {v:,}" for k, v in dc.items()),
        f"- Retired: {h['retired_total']:,} endpoints ({newly:,} today); revived today: {revived:,}",
        f"- Failing but not yet retired: {len(fails):,}",
        f"- Hosts down today (80%+ of 20+ services failed): {', '.join(sorted(down)) or 'none'}",
        f"- Publisher text changes today: {retag_n:,} datasets. {retag_note}",
        "", "## Hosts with most failing endpoints", "",
        *[f"- {k}: {v:,}" for k, v in top.items()],
        "", "Rules: resolving services rechecked every 7 days, failing every 3, retired every 28. Retired after 3 failed",
        "checks over 14+ days (30 when the whole host was down). Robots.txt refusals are not failures.",
    ]
    return "\n".join(lines) + "\n", h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datasets", required=True, help="published datasets (passing, before liveness is applied)")
    ap.add_argument("--layers", required=True, help="combined layers with uid, title, abstract")
    ap.add_argument("--state", default="")
    ap.add_argument("--history", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--minutes", type=float, default=240)
    ap.add_argument("--max-services", type=int, default=45_000)
    ap.add_argument("--retag-cap", type=int, default=50_000, help="above this many changed datasets, don't re-tag (ask first)")
    ap.add_argument("--today", default="")
    ap.add_argument("--started", default="", help="run start time for history.csv (default: when this script started)")
    ap.add_argument("--only-host", default="", help="testing: only services on hosts containing this text")
    a = ap.parse_args()
    t0 = time.monotonic()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    today = date.fromisoformat(a.today) if a.today else date.today()

    pop = population(a.datasets, a.layers)
    st = load_state(a.state)
    # --only-host narrows what is checked, never the state: everything else is carried over untouched
    sel = pop[pop["service_url"].str.contains(a.only_host, regex=False)] if a.only_host else pop
    services = due_services(sel, st, today, a.max_services, seed=7)
    print(f"{len(pop):,} endpoints; {len(services):,} services due today", flush=True)
    week = (today - date(2026, 1, 5)).days // 7
    results, stats = asyncio.run(run_checks(services, t0 + a.minutes * 60, week))
    print(f"checked {len(results):,} services", flush=True)
    st, outcomes, retag, down = apply(pop, st, results, today)

    changes = st[st["cur_title"].notna() | st["cur_abstract"].notna()][
        ["uid", "dataset_id", "orig_title", "orig_abstract", "cur_title", "cur_abstract", "text_changed"]]
    changes.to_parquet(out / "changes.parquet")
    note = ""
    rt = patched_datasets(a.datasets, changes, retag) if retag else None
    if rt is not None and len(rt):
        if len(rt) <= a.retag_cap:
            rt.to_parquet(out / "retag.parquet")
            note = f"{len(rt):,} sent for re-tagging (~${len(rt) * 0.09 / 1000:.2f})."
        else:
            note = f"{len(rt):,} is over the re-tag cap of {a.retag_cap:,}: not re-tagged, needs a look."
    st[STATE_COLS].to_parquet(out / "state.parquet", compression="zstd")
    md, h = report(st, outcomes, results, down, len(rt) if rt is not None else 0, note, today,
                   time.monotonic() - t0, stats, len(services))
    (out / "REPORT.md").write_text(md)
    # one line per run, not per date: a delayed scheduled run can land on the same UTC day as a manual one, and both
    # are worth keeping. "started" (UTC) tells them apart; it also shows how late GitHub started a scheduled run.
    h = {**h, "trigger": os.environ.get("GITHUB_EVENT_NAME", ""), "started": a.started or time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(time.time() - (time.monotonic() - t0)))}
    hist = pd.read_csv(a.history) if a.history and Path(a.history).exists() else pd.DataFrame()
    hist = pd.concat([hist, pd.DataFrame([h])])
    hist.to_csv(out / "history.csv", index=False)
    print(md)


if __name__ == "__main__":
    main()
