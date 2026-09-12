"""Arweave — the permaweb: permanent, arbitrary-content storage. A natural fit for
agents wanting durable shared state. We query the GraphQL gateway for recent
text/plain transactions and fetch their data. Read-only.
"""

from __future__ import annotations

import json
from typing import Iterator

from ...config import CONFIG
from ...models import Candidate
from ..base import Collector, http_get
from ..registry import register
from . import payload_text

GRAPHQL = "https://arweave.net/graphql"
GATEWAY = "https://arweave.net/"

try:
    import requests  # type: ignore
except Exception:  # pragma: no cover
    requests = None  # type: ignore

_QUERY = """
query($n: Int!) {
  transactions(first: $n, tags: [{name: "Content-Type", values: ["text/plain"]}]) {
    edges { node { id owner { address } block { timestamp } } }
  }
}
"""


class ArweaveCollector(Collector):
    name = "arweave"
    requires_active = True

    def iter_candidates(self, since=None, limit=100) -> Iterator[Candidate]:
        if requests is None:
            return
        try:
            r = requests.post(GRAPHQL, timeout=20,
                              headers={"User-Agent": CONFIG.user_agent, "content-type": "application/json"},
                              data=json.dumps({"query": _QUERY, "variables": {"n": min(limit, 100)}}))
            edges = r.json()["data"]["transactions"]["edges"] if r.status_code == 200 else []
        except Exception:
            return
        n = 0
        for e in edges:
            node = e.get("node", {})
            txid = node.get("id")
            if not txid:
                continue
            data = http_get(GATEWAY + txid)
            if data is None:
                continue
            text = payload_text(data.content)
            if not text:
                continue
            yield Candidate(
                source=self.name, locator=GATEWAY + txid, content=text,
                author=(node.get("owner") or {}).get("address"),
                ts=str((node.get("block") or {}).get("timestamp", "")),
                meta={"chain": "arweave"})
            n += 1
            if n >= limit:
                return


register(ArweaveCollector())
