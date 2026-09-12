"""Common Crawl — the big offline web scrape (passive; hits CC infra only).

Queries the CC index for URL patterns, then fetches each matched record's payload
via an HTTP range request against data.commoncrawl.org and extracts the response
body from the WARC record. Configure the crawl and URL patterns with env:
  LAPIS_CC_CRAWL   (default: latest known main crawl id)
  LAPIS_CC_PATTERNS (csv of url patterns, e.g. "*.wikiservice.at/*,pastebin.com/*")
"""

from __future__ import annotations

import gzip
import os
from typing import Iterator

from ..models import Candidate
from .base import Collector, http_get
from .registry import register

INDEX = "https://index.commoncrawl.org/{crawl}-index"
DATA = "https://data.commoncrawl.org/"
COLLINFO = "https://index.commoncrawl.org/collinfo.json"
_FALLBACK_CRAWL = "CC-MAIN-2026-34"


def _resolve_crawl() -> str:
    """LAPIS_CC_CRAWL if set, else the newest published crawl (crawls aren't
    weekly, so a hardcoded id goes stale and 404s). Falls back to a known id."""
    env = os.environ.get("LAPIS_CC_CRAWL")
    if env:
        return env
    r = http_get(COLLINFO)
    if r is not None:
        try:
            return r.json()[0]["id"]
        except Exception:
            pass
    return _FALLBACK_CRAWL


DEFAULT_PATTERNS = os.environ.get(
    "LAPIS_CC_PATTERNS", "*.wikiservice.at/*,prowiki.org/*").split(",")


def _extract_body(warc_gz: bytes) -> str | None:
    """A WARC record is: WARC headers, blank line, HTTP headers, blank line, body."""
    try:
        raw = gzip.decompress(warc_gz)
    except Exception:
        raw = warc_gz
    # Split off the HTTP response body (after the second blank line).
    parts = raw.split(b"\r\n\r\n", 2)
    if len(parts) < 3:
        return None
    body = parts[2]
    try:
        return body.decode("utf-8", "replace")
    except Exception:
        return None


class CommonCrawlCollector(Collector):
    name = "commoncrawl"
    requires_active = False   # passive: CC infra, not third-party origins

    def iter_candidates(self, since=None, limit=100) -> Iterator[Candidate]:
        crawl = _resolve_crawl()
        n = 0
        for pattern in DEFAULT_PATTERNS:
            pattern = pattern.strip()
            if not pattern:
                continue
            r = http_get(INDEX.format(crawl=crawl),
                         params={"url": pattern, "output": "json", "limit": limit})
            if r is None:
                continue
            for line in r.text.splitlines():
                if not line.strip():
                    continue
                import json
                try:
                    rec = json.loads(line)
                    off, length = int(rec["offset"]), int(rec["length"])
                    warc = rec["filename"]
                except Exception:
                    continue
                rng = http_get(DATA + warc,
                               headers={"Range": f"bytes={off}-{off + length - 1}"})
                if rng is None:
                    continue
                body = _extract_body(rng.content)
                if not body or not body.strip():
                    continue
                yield Candidate(
                    source=self.name,
                    locator=rec.get("url", warc),
                    content=body,
                    ts=rec.get("timestamp"),
                    meta={"crawl": crawl, "pattern": pattern},
                )
                n += 1
                if n >= limit:
                    return


register(CommonCrawlCollector())
