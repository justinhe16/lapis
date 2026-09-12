"""Ephemeral relays & bins — no-auth write/relay surfaces agents use as scratch
coordination. These have no global listing, so you scan *known* locators: topics,
bins, tokens (often surfaced by enumerate.py or seen in other candidates).

Configure:
  LAPIS_NTFY_TOPICS   = csv of ntfy.sh topics to poll (cached messages)
  LAPIS_JSONBINS      = csv of full bin URLs (jsonbin/npoint/etc.) to read
"""

from __future__ import annotations

import os
from typing import Iterator

from ..models import Candidate
from .base import Collector, http_get
from .registry import register

NTFY_TOPICS = [t.strip() for t in os.environ.get("LAPIS_NTFY_TOPICS", "").split(",") if t.strip()]
JSONBINS = [b.strip() for b in os.environ.get("LAPIS_JSONBINS", "").split(",") if b.strip()]


class RelaysCollector(Collector):
    name = "relays"
    requires_active = True

    def iter_candidates(self, since=None, limit=100) -> Iterator[Candidate]:
        n = 0
        for topic in NTFY_TOPICS:
            # ntfy caches recent messages; poll=1 returns them without holding open.
            r = http_get(f"https://ntfy.sh/{topic}/json", params={"poll": "1"})
            if r is None:
                continue
            for line in r.text.splitlines():
                if not line.strip():
                    continue
                import json
                try:
                    msg = json.loads(line)
                except Exception:
                    continue
                body = msg.get("message") or ""
                if not body:
                    continue
                yield Candidate(
                    source=self.name, locator=f"https://ntfy.sh/{topic}",
                    content=body, ts=str(msg.get("time", "")),
                    meta={"kind": "ntfy", "topic": topic})
                n += 1
                if n >= limit:
                    return
        for url in JSONBINS:
            r = http_get(url)
            if r is None:
                continue
            yield Candidate(source=self.name, locator=url, content=r.text,
                            meta={"kind": "jsonbin"})
            n += 1
            if n >= limit:
                return


register(RelaysCollector())
