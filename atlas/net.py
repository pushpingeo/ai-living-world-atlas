"""Polite async HTTP client: one user agent, per-host limits, robots.txt, timeouts."""
from __future__ import annotations

import asyncio
import time
import urllib.robotparser
from dataclasses import dataclass
from urllib.parse import urlsplit

import aiohttp

VIEWER_ORIGIN = "https://pushpingeo.github.io"  # sent so servers reveal whether a browser app may use them
USER_AGENT = (
    "AI-Living-World-Atlas/0.1 (+https://github.com/pushpingeo/ai-living-world-atlas; "
    "open index of public map services)"
)


@dataclass
class Resp:
    url: str
    status: int  # 0 = network error / timeout
    ms: int
    body: bytes = b""
    content_type: str = ""
    error: str = ""
    cors: bool | None = None  # did the server allow a browser page on another site to read this?

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300

    def json(self):
        import json

        return json.loads(self.body)


class Client:
    def __init__(self, total: int = 32, per_host: int = 2, timeout: float = 25, max_bytes: int = 30_000_000):
        self.total = asyncio.Semaphore(total)
        self.per_host: dict[str, asyncio.Semaphore] = {}
        self.per_host_n = per_host
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_bytes = max_bytes
        self.robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}
        self.robots_lock: dict[str, asyncio.Lock] = {}
        self.session: aiohttp.ClientSession | None = None
        self.stats = {"requests": 0, "errors": 0, "robots_blocked": 0}

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={"User-Agent": USER_AGENT, "Accept-Encoding": "gzip, deflate", "Origin": VIEWER_ORIGIN},
            connector=aiohttp.TCPConnector(limit=0, ttl_dns_cache=600),
        )
        return self

    async def __aexit__(self, *a):
        await self.session.close()

    def _host_sem(self, host: str) -> asyncio.Semaphore:
        if host not in self.per_host:
            self.per_host[host] = asyncio.Semaphore(self.per_host_n)
        return self.per_host[host]

    async def _allowed(self, url: str) -> bool:
        p = urlsplit(url)
        key = f"{p.scheme}://{p.netloc}"
        lock = self.robots_lock.setdefault(key, asyncio.Lock())
        async with lock:
            if key not in self.robots:
                rp = None
                try:
                    async with self.session.get(key + "/robots.txt", timeout=aiohttp.ClientTimeout(total=10)) as r:
                        if r.status == 200 and "text" in r.headers.get("Content-Type", "text"):
                            txt = (await r.read()).decode("utf-8", "replace")[:200_000]
                            rp = urllib.robotparser.RobotFileParser()
                            rp.parse(txt.splitlines())
                except Exception:
                    rp = None
                self.robots[key] = rp
        rp = self.robots[key]
        return True if rp is None else rp.can_fetch(USER_AGENT, url)

    async def post_json(self, url: str, body: dict, retries: int = 2) -> Resp:
        """POST a JSON body (for search APIs). Same politeness rules as get()."""
        host = urlsplit(url).netloc
        last = None
        for attempt in range(retries + 1):
            async with self.total, self._host_sem(host):
                t0 = time.monotonic()
                self.stats["requests"] += 1
                try:
                    async with self.session.post(url, json=body, timeout=aiohttp.ClientTimeout(total=120),
                                                 headers={"Accept": "application/json"}) as r:
                        data = await r.read()
                        last = Resp(str(r.url), r.status, int((time.monotonic() - t0) * 1000), data, r.headers.get("Content-Type", ""))
                except Exception as e:
                    last = Resp(url, 0, int((time.monotonic() - t0) * 1000), error=f"{type(e).__name__}: {e}"[:200])
            if last.status in (0, 429, 502, 503, 504) and attempt < retries:
                await asyncio.sleep(3 * (attempt + 1))
                continue
            break
        if not last.ok:
            self.stats["errors"] += 1
        return last

    async def get(self, url: str, retries: int = 1, timeout: float | None = None) -> Resp:
        host = urlsplit(url).netloc
        if not await self._allowed(url):
            self.stats["robots_blocked"] += 1
            return Resp(url, 0, 0, error="robots.txt disallows")
        last = None
        for attempt in range(retries + 1):
            async with self.total, self._host_sem(host):
                t0 = time.monotonic()
                self.stats["requests"] += 1
                try:
                    async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=timeout) if timeout else self.timeout, allow_redirects=True) as r:
                        chunks, size = [], 0
                        async for chunk in r.content.iter_chunked(1 << 16):
                            chunks.append(chunk)
                            size += len(chunk)
                            if size >= self.max_bytes:
                                break
                        body = b"".join(chunks)
                        ms = int((time.monotonic() - t0) * 1000)
                        acao = r.headers.get("Access-Control-Allow-Origin", "")
                        last = Resp(str(r.url), r.status, ms, body, r.headers.get("Content-Type", ""),
                                    cors=acao.strip() in ("*", VIEWER_ORIGIN))
                except Exception as e:  # network error, timeout, TLS
                    ms = int((time.monotonic() - t0) * 1000)
                    last = Resp(url, 0, ms, error=f"{type(e).__name__}: {e}"[:200])
            if last.status in (0, 429, 502, 503, 504) and attempt < retries:
                await asyncio.sleep(2 * (attempt + 1))
                continue
            break
        if not last.ok:
            self.stats["errors"] += 1
        return last
