"""Paste sites — no-auth text drops agents use as scratch coordination.

v1 reads Pastebin's public archive and raw bodies. Read-only, rate-limited, and
UA-identified.

ToS note: some paste sites restrict scraping. Check the target's Terms before
enabling this collector, prefer an official API/dump where one exists, and keep
LAPIS_RATE_PER_HOST conservative. Common Crawl is the lower-friction alternative
for historical paste content.
"""

from __future__ import annotations

import re
from typing import Iterator

from ..models import Candidate
from .base import Collector, http_get
from .registry import register

ARCHIVE = "https://pastebin.com/archive"
RAW = "https://pastebin.com/raw/{key}"
# Pastebin archive rows link to /<8-char key>, now with a ?source=archive suffix.
_KEY = re.compile(r'href="/([A-Za-z0-9]{8})(?:\?[^"]*)?"')


class PastesCollector(Collector):
    name = "pastes"
    requires_active = True

    def iter_candidates(self, since=None, limit=100) -> Iterator[Candidate]:
        r = http_get(ARCHIVE)
        if r is None:
            return
        keys, seen = [], set()
        for m in _KEY.finditer(r.text):
            k = m.group(1)
            if k not in seen:
                seen.add(k)
                keys.append(k)
        for key in keys[:limit]:
            raw = http_get(RAW.format(key=key))
            if raw is None or not raw.text.strip():
                continue
            yield Candidate(
                source=self.name,
                locator=f"https://pastebin.com/{key}",
                content=raw.text,
                meta={"site": "pastebin"},
            )


register(PastesCollector())
