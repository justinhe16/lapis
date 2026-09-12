"""Ethereum — transaction calldata (and, later, event log data) can carry arbitrary
bytes cheaply (especially on L2s). We scan recent blocks' tx `input` fields, decode
to text, and yield anything readable.

Needs a JSON-RPC endpoint:  ETH_RPC_URL  (any provider; read-only eth_ calls).
"""

from __future__ import annotations

import json
from typing import Iterator

from ...config import CONFIG
from ...models import Candidate
from ..base import Collector
from ..registry import register
from . import hex_to_text

try:
    import requests  # type: ignore
except Exception:  # pragma: no cover
    requests = None  # type: ignore


def _rpc(method: str, params: list):
    if requests is None or not CONFIG.eth_rpc:
        return None
    try:
        r = requests.post(CONFIG.eth_rpc, timeout=20,
                          headers={"User-Agent": CONFIG.user_agent, "content-type": "application/json"},
                          data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}))
        return r.json().get("result") if r.status_code == 200 else None
    except Exception:
        return None


class EthereumCollector(Collector):
    name = "eth"
    requires_active = True

    def iter_candidates(self, since=None, limit=100) -> Iterator[Candidate]:
        tip = _rpc("eth_blockNumber", [])
        if not tip:
            return
        tip = int(tip, 16)
        n = 0
        block = tip
        while block > 0 and n < limit:
            b = _rpc("eth_getBlockByNumber", [hex(block), True])
            block -= 1
            if not b:
                continue
            for tx in b.get("transactions", []):
                inp = tx.get("input", "0x")
                # skip empty or pure-selector calldata (4 bytes)
                if len(inp) <= 10:
                    continue
                text = hex_to_text(inp)
                if not text:
                    continue
                yield Candidate(
                    source=self.name, locator=tx.get("hash", ""),
                    content=text, author=tx.get("from"),
                    meta={"chain": "ethereum", "to": tx.get("to"), "block": int(b.get("number", "0x0"), 16)})
                n += 1
                if n >= limit:
                    return


register(EthereumCollector())
