"""Agreement test: Haiku (the tagger we'd run at scale) vs Opus (stronger, independent labeller).

Also scores both against what publishers declared themselves, where they did.
Usage: python -m atlas.eval_tags --datasets datasets.parquet --layers layers.parquet --n 200 --out out/eval
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

import aiohttp
import pandas as pd

from .tagging import Tagger, describe

PRICES = {"claude-haiku-5-5": (0.10, 0.50), "claude-opus-5-5": (4.0, 20.0)}  # $ per M tokens, standard rate


def sample(ds: pd.DataFrame, n: int, seed: int = 11) -> pd.DataFrame:
    p = ds[ds["q_pass"]].copy()
    declared = p[p["iso_themes_declared"].apply(len) > 0]
    k = min(len(declared), n // 4)  # a quarter with publisher-declared themes, so we can check against them
    a = declared.sample(k, random_state=seed)
    b = p.drop(a.index).sample(n - k, random_state=seed)
    return pd.concat([a, b])


def overlap(a, b) -> float:
    a, b = set(a or []), set(b or [])
    return len(a & b) / len(a | b) if a | b else 1.0


async def run(args):
    ds = pd.read_parquet(args.datasets)
    layers = pd.read_parquet(args.layers, columns=["uid", "dataset_id", "fields"])
    fields = layers.groupby("dataset_id")["fields"].apply(lambda s: max((list(x) for x in s), key=len, default=[])).to_dict()
    s = sample(ds, args.n)
    texts = [describe(r, fields.get(r["dataset_id"])) for r in s.to_dict("records")]
    haiku, opus = Tagger("claude-haiku-5-5", 6), Tagger("claude-opus-5-5", 4)
    async with aiohttp.ClientSession() as session:
        h = await asyncio.gather(*[haiku.tag(session, t) for t in texts])
        o = await asyncio.gather(*[opus.tag(session, t) for t in texts])
    s = s.assign(prompt=texts, haiku=[json.dumps(x) for x in h], opus=[json.dumps(x) for x in o])
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    s.drop(columns=[c for c in s.columns if c == "geometry"]).to_parquet(out / "labels.parquet")
    report(s, h, o, haiku, opus, out)


def report(s, h, o, haiku, opus, out):
    rows = []
    for (_, r), hh, oo in zip(s.iterrows(), h, o):
        if "error" in hh or "error" in oo:
            rows.append({"error": True})
            continue
        dec = list(r["iso_themes_declared"])
        rows.append({
            "error": False,
            "theme1_agree": bool(hh["iso_themes"] and oo["iso_themes"] and hh["iso_themes"][0] == oo["iso_themes"][0]),
            "theme_any": bool(set(hh["iso_themes"]) & set(oo["iso_themes"])),
            "theme_jaccard": overlap(hh["iso_themes"], oo["iso_themes"]),
            "concept1_agree": bool(hh["concepts"] and oo["concepts"] and hh["concepts"][0] == oo["concepts"][0]),
            "concept_any": bool(set(hh["concepts"]) & set(oo["concepts"])) if (hh["concepts"] or oo["concepts"]) else True,
            "concept_jaccard": overlap(hh["concepts"], oo["concepts"]),
            "haiku_no_concept": not hh["concepts"], "opus_no_concept": not oo["concepts"],
            "has_declared": bool(dec),
            "haiku_hits_declared": bool(set(hh["iso_themes"]) & set(dec)) if dec else None,
            "opus_hits_declared": bool(set(oo["iso_themes"]) & set(dec)) if dec else None,
            "haiku_invalid": len(hh.get("invalid", [])), "opus_invalid": len(oo.get("invalid", [])),
            "haiku_proposed": hh.get("proposed_concept", ""), "opus_proposed": oo.get("proposed_concept", ""),
        })
    m = pd.DataFrame(rows)
    ok = m[~m["error"]]
    d = ok[ok["has_declared"]]

    def pct(x):
        return f"{100 * float(x):.0f}%"

    def cost(t, model):
        pi, po = PRICES[model]
        return t.usage["input_tokens"] / 1e6 * pi + t.usage["output_tokens"] / 1e6 * po

    disagreements = []
    for (_, r), hh, oo in zip(s.iterrows(), h, o):
        if "error" in hh or "error" in oo:
            continue
        if hh["concepts"][:1] != oo["concepts"][:1]:
            disagreements.append(f"- **{r['title'][:70]}** ({r['publisher'][:40]}): Haiku {hh['concepts']} / Opus {oo['concepts']}")
    proposed = pd.Series([p for p in list(ok["haiku_proposed"]) + list(ok["opus_proposed"]) if p]).value_counts().head(15)
    lines = [
        "# AI tagging agreement: Haiku 5.5 vs Opus 5.5",
        "",
        f"{len(s)} passing UK datasets ({int(ok['has_declared'].sum())} with publisher-declared themes); {int(m['error'].sum())} errors.",
        "",
        "## Themes (ISO 19115)",
        f"- First theme identical: **{pct(ok['theme1_agree'].mean())}**; any theme shared: {pct(ok['theme_any'].mean())}; mean overlap {ok['theme_jaccard'].mean():.2f}",
        f"- Against publisher-declared themes ({len(d)} datasets): Haiku matches {pct(d['haiku_hits_declared'].mean()) if len(d) else 'n/a'}, Opus matches {pct(d['opus_hits_declared'].mean()) if len(d) else 'n/a'}",
        "",
        "## Concepts",
        f"- First concept identical: **{pct(ok['concept1_agree'].mean())}**; any concept shared (or both none): {pct(ok['concept_any'].mean())}; mean overlap {ok['concept_jaccard'].mean():.2f}",
        f"- No concept fits: Haiku {pct(ok['haiku_no_concept'].mean())}, Opus {pct(ok['opus_no_concept'].mean())}",
        f"- Out-of-vocabulary answers (dropped): Haiku {int(ok['haiku_invalid'].sum())}, Opus {int(ok['opus_invalid'].sum())}",
        "",
        "## Proposed new concepts (both models)",
        *[f"- {k}: {v}" for k, v in proposed.items()],
        "",
        "## Cost of this test",
        f"- Haiku: {haiku.usage['calls']} calls, ${cost(haiku, 'claude-haiku-5-5'):.2f}; Opus: {opus.usage['calls']} calls, ${cost(opus, 'claude-opus-5-5'):.2f}",
        f"- Haiku at batch rates would tag 100k datasets for about ${cost(haiku, 'claude-haiku-5-5') / max(haiku.usage['calls'], 1) * 100_000 / 2:.0f}",
        "",
        "## First-concept disagreements (up to 40)",
        *disagreements[:40],
    ]
    (out / "REPORT.md").write_text("\n".join(lines) + "\n")
    (out / "metrics.json").write_text(json.dumps({"haiku_usage": haiku.usage, "opus_usage": opus.usage,
                                                   "summary": ok.drop(columns=["haiku_proposed", "opus_proposed"]).mean(numeric_only=True).to_dict()}, indent=1))
    print("\n".join(lines[:20]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datasets", required=True)
    ap.add_argument("--layers", required=True)
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--out", default="out/eval")
    asyncio.run(run(ap.parse_args()))


if __name__ == "__main__":
    main()
