"""IPFS — content-addressed storage. There is no global listing, so IPFS is scanned
by *known* CIDs (surfaced by enumerate.py, or seen referenced in other candidates).
Fetches each CID through a public gateway and decodes to text.

Configure:  LAPIS_IPFS_CIDS = csv of CIDs to fetch
"""

from __future__ import annotations

import os
from typing import Iterator

from ...models import Candidate
from ..base import Collector, http_get
from ..registry import register
from . import payload_text

GATEWAY = os.environ.get("LAPIS_IPFS_GATEWAY", "https://ipfs.io/ipfs/")
CIDS = [c.strip() for c in os.environ.get("LAPIS_IPFS_CIDS", "").split(",") if c.strip()]


class IPFSCollector(Collector):
    name = "ipfs"
    requires_active = True

    def iter_candidates(self, since=None, limit=100) -> Iterator[Candidate]:
        n = 0
        for cid in CIDS:
            r = http_get(GATEWAY + cid)
            if r is None:
                continue
            text = payload_text(r.content)
            if not text:
                continue
            yield Candidate(source=self.name, locator=GATEWAY + cid, content=text,
                            meta={"chain": "ipfs", "cid": cid})
            n += 1
            if n >= limit:
                return


register(IPFSCollector())
