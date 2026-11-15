"""AI theme and concept tagging, constrained to the fixed vocabularies.

The model may only choose from vocab/themes.yaml (ISO topic categories) and vocab/concepts.yaml.
If nothing fits it can propose a concept, which a person reviews before it joins the list.
"""
from __future__ import annotations

import asyncio
import json
import os
from functools import lru_cache
from pathlib import Path

import aiohttp
import yaml

API = "https://api.anthropic.com/v1/messages"
ROOT = Path(__file__).resolve().parent.parent


@lru_cache
def vocab():
    themes = yaml.safe_load((ROOT / "vocab/themes.yaml").read_text())["iso_topic_categories"]
    concepts = yaml.safe_load((ROOT / "vocab/concepts.yaml").read_text())
    return themes, concepts


def system_prompt() -> str:
    themes, concepts = vocab()
    t = "\n".join(f"- {k}: {v}" for k, v in themes.items())
    c = "\n".join(f"- {k} ({v['theme']}): {v['def']}" for k, v in concepts.items())
    return f"""You catalogue public map layers for an open index used by AI agents.
Given one dataset's metadata, choose:
1. iso_themes: 1-3 ISO 19115 topic categories, most important first. Only these codes:
{t}
2. concepts: 0-4 concepts describing what the data actually is, most specific first. Only these ids:
{c}
Pick a concept only when the data clearly is that thing. An empty list is better than a loose fit.
3. proposed_concept: if the data is a clear, reusable kind of thing that no concept covers, a short kebab-case id; otherwise "".

Judge from the evidence: title, description, field names, publisher, service type. Ignore boilerplate
(contact details, disclaimers, licence text). Do not guess from the publisher alone.
Always answer by calling the record_tags tool, once."""


TOOL = {
    "name": "record_tags",
    "description": "Record the chosen tags for this dataset.",
    "input_schema": {
        "type": "object",
        "properties": {
            "iso_themes": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 3},
            "concepts": {"type": "array", "items": {"type": "string"}, "maxItems": 4},
            "proposed_concept": {"type": "string"},
            "confidence": {"type": "number", "description": "0-1, how sure you are of the first theme and concept"},
            "reason": {"type": "string", "description": "one short sentence"},
        },
        "required": ["iso_themes", "concepts", "proposed_concept", "confidence", "reason"],
    },
}


def describe(ds: dict, fields: list[str] | None = None) -> str:
    """The evidence we show the model. Kept short: title, description, fields, publisher, shape."""
    def lst(v):
        return [] if v is None else list(v)

    abstract = (ds.get("abstract") or "")[:1500]
    f = ", ".join(x.split("|")[0] for x in (fields or [])[:40])
    return "\n".join(x for x in [
        f"Title: {ds.get('title')}",
        f"Publisher: {ds.get('publisher')} ({ds.get('publisher_type')})",
        f"Service types: {', '.join(lst(ds.get('protocols')))}; role: {ds.get('role')}",
        f"Keywords: {', '.join(lst(ds.get('keywords'))[:20])}" if lst(ds.get("keywords")) else "",
        f"Fields: {f}" if f else "",
        f"Description: {abstract}" if abstract else "Description: (none)",
    ] if x)


def clean(out: dict) -> dict:
    """Drop anything outside the vocabularies; the model is told not to, but we don't trust it blindly."""
    themes, concepts = vocab()
    return {
        "iso_themes": [t for t in out.get("iso_themes", []) if t in themes][:3],
        "concepts": [c for c in out.get("concepts", []) if c in concepts][:4],
        "invalid": [x for x in out.get("iso_themes", []) + out.get("concepts", []) if x not in themes and x not in concepts],
        "proposed_concept": (out.get("proposed_concept") or "").strip().strip('"').strip(),
        "confidence": out.get("confidence"),
        "reason": (out.get("reason") or "")[:300],
    }


class Tagger:
    def __init__(self, model: str, concurrency: int = 4):
        self.model = model
        self.sem = asyncio.Semaphore(concurrency)
        self.key = os.environ["ANTHROPIC_API_KEY"]
        self.usage = {"input_tokens": 0, "output_tokens": 0, "calls": 0, "errors": 0}

    async def tag(self, session: aiohttp.ClientSession, text: str) -> dict:
        body = {
            "model": self.model, "max_tokens": 600, "system": system_prompt(),
            "tools": [TOOL],
            # some models refuse a forced tool call; there we ask for it in the prompt instead
            "tool_choice": {"type": "tool", "name": "record_tags"} if "haiku" in self.model else {"type": "auto"},
            "messages": [{"role": "user", "content": text}],
        }
        headers = {"x-api-key": self.key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
        async with self.sem:
            for attempt in range(5):
                try:
                    async with session.post(API, json=body, headers=headers, timeout=aiohttp.ClientTimeout(total=120)) as r:
                        j = await r.json()
                        if r.status in (429, 500, 502, 503, 529):
                            await asyncio.sleep(2 ** attempt * 3)
                            continue
                        if r.status != 200:
                            self.usage["errors"] += 1
                            return {"error": f"HTTP {r.status}: {str(j)[:200]}"}
                        self.usage["calls"] += 1
                        for k in ("input_tokens", "output_tokens"):
                            self.usage[k] += (j.get("usage") or {}).get(k, 0)
                        block = next((b for b in j.get("content", []) if b.get("type") == "tool_use"), None)
                        return clean(block["input"]) if block else {"error": "no tool call"}
                except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                    await asyncio.sleep(2 ** attempt * 3)
                    last = str(e)
            self.usage["errors"] += 1
            return {"error": "retries exhausted"}
