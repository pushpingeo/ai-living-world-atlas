"""Tag datasets with Haiku through the Message Batches API (half price), then collect the results.

python -m atlas.tag_batch --datasets datasets.parquet --layers layers.parquet --out out/tags [--only-passing]
Large jobs are split into several batches (the API caps a batch's size). Resume with --batch-id id1,id2,...
Writes tags.parquet and COST.md.
"""
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.request
from pathlib import Path

import pandas as pd

from .tagging import TOOL, clean, describe, system_prompt

API = "https://api.anthropic.com/v1/messages/batches"
MODEL = "claude-haiku-5-5"
MAX_BATCH_BYTES = 90_000_000  # well under the API's 256 MB cap per batch
MAX_BATCH_REQUESTS = 50_000
BATCH_PRICE = {"in": 0.05, "out": 0.25, "cache_read": 0.005, "cache_write": 0.0625}  # $ per M tokens


def _req(method, url, body=None):
    headers = {"x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01", "content-type": "application/json"}
    data = json.dumps(body).encode() if body is not None else None
    with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers, method=method), timeout=300) as r:
        return r.read()


def build_requests(ds: pd.DataFrame, fields: dict) -> list[dict]:
    system = [{"type": "text", "text": system_prompt(), "cache_control": {"type": "ephemeral"}}]
    out = []
    for r in ds.to_dict("records"):
        out.append({"custom_id": r["dataset_id"], "params": {
            "model": MODEL, "max_tokens": 400, "system": system, "tools": [TOOL],
            "tool_choice": {"type": "tool", "name": "record_tags"},
            "messages": [{"role": "user", "content": describe(r, fields.get(r["dataset_id"]))}],
        }})
    return out


def chunks(reqs: list[dict]):
    batch, size = [], 0
    for r in reqs:
        n = len(json.dumps(r))
        if batch and (size + n > MAX_BATCH_BYTES or len(batch) >= MAX_BATCH_REQUESTS):
            yield batch
            batch, size = [], 0
        batch.append(r)
        size += n
    if batch:
        yield batch


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datasets", required=True)
    ap.add_argument("--layers", required=True)
    ap.add_argument("--out", default="out/tags")
    ap.add_argument("--only-passing", action="store_true")
    ap.add_argument("--batch-id", default="")
    ap.add_argument("--skip-tagged", default="", help="tags.parquet of datasets already tagged; those are skipped")
    ap.add_argument("--max-wait-min", type=float, default=320)
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    bid = args.batch_id
    if not bid:
        ds = pd.read_parquet(args.datasets)
        if args.only_passing:
            ds = ds[ds["q_pass"]]
        if args.skip_tagged and Path(args.skip_tagged).exists():
            done = set(pd.read_parquet(args.skip_tagged, columns=["dataset_id"])["dataset_id"])
            before = len(ds)
            ds = ds[~ds["dataset_id"].isin(done)]
            print(f"skipping {before - len(ds)} already tagged", flush=True)
        if not len(ds):
            (out / "COST.md").write_text("# Nothing new to tag\n\n- **Cost: $0.00**\n")
            print("nothing to tag")
            return
        layers = pd.read_parquet(args.layers, columns=["dataset_id", "fields"])
        fields = layers.groupby("dataset_id")["fields"].apply(lambda s: max((list(x) for x in s), key=len, default=[])).to_dict()
        reqs = build_requests(ds, fields)
        ids = []
        for chunk in chunks(reqs):
            res = json.loads(_req("POST", API, {"requests": chunk}))
            ids.append(res["id"])
            print(f"submitted batch {res['id']} with {len(chunk)} requests", flush=True)
        bid = ",".join(ids)
    (out / "BATCH_ID").write_text(bid)
    ids = bid.split(",")

    t0 = time.time()
    status = {}
    while True:
        for i in ids:
            if status.get(i, {}).get("processing_status") != "ended":
                status[i] = json.loads(_req("GET", f"{API}/{i}"))
        print(f"[{int(time.time() - t0)}s] " + "; ".join(f"{i[-6:]} {st['processing_status']} {st.get('request_counts')}" for i, st in status.items()), flush=True)
        if all(st["processing_status"] == "ended" for st in status.values()):
            break
        if time.time() - t0 > args.max_wait_min * 60:
            (out / "STATUS.txt").write_text(f"batches {bid} still running; resume with --batch-id {bid}\n")
            return
        time.sleep(60)

    rows, usage = [], {"input_tokens": 0, "output_tokens": 0, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}
    lines = [ln for st in status.values() for ln in _req("GET", st["results_url"]).decode().splitlines()]
    for line in lines:
        if not line.strip():
            continue
        j = json.loads(line)
        res = j["result"]
        row = {"dataset_id": j["custom_id"], "status": res["type"]}
        if res["type"] == "succeeded":
            msg = res["message"]
            for k in usage:
                usage[k] += (msg.get("usage") or {}).get(k) or 0
            block = next((b for b in msg["content"] if b.get("type") == "tool_use"), None)
            if block:
                row.update(clean(block["input"]))
        rows.append(row)
    df = pd.DataFrame(rows)
    df["tag_model"] = MODEL
    df["tagged_at"] = time.strftime("%Y-%m-%d")
    df.to_parquet(out / "tags.parquet")
    cost = (usage["input_tokens"] * BATCH_PRICE["in"] + usage["output_tokens"] * BATCH_PRICE["out"]
            + usage["cache_read_input_tokens"] * BATCH_PRICE["cache_read"]
            + usage["cache_creation_input_tokens"] * BATCH_PRICE["cache_write"]) / 1e6
    ok = (df["status"] == "succeeded").sum()
    (out / "COST.md").write_text(
        f"# Tagging batch(es) {bid}\n\n- Requests: {len(df)}; succeeded: {ok}\n- Model: {MODEL} (batch rates)\n"
        f"- Tokens: {json.dumps(usage)}\n- **Cost: ${cost:.2f}** (estimated from token counts and published batch prices)\n")
    print((out / "COST.md").read_text())


if __name__ == "__main__":
    main()
