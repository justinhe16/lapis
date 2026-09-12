"""Bitcoin — OP_RETURN outputs carry up to 80 bytes of arbitrary data per tx (and
inscriptions carry far more). We read recent blocks via the public blockstream.info
API (no key), pull OP_RETURN data, and decode to text. Read-only.
"""

from __future__ import annotations

from typing import Iterator

from ...models import Candidate
from ..base import Collector, http_get
from ..registry import register
from . import hex_to_text

API = "https://blockstream.info/api"


class BitcoinCollector(Collector):
    name = "btc"
    requires_active = True

    def iter_candidates(self, since=None, limit=100) -> Iterator[Candidate]:
        tip = http_get(f"{API}/blocks/tip/height")
        if tip is None:
            return
        try:
            height = int(tip.text.strip())
        except Exception:
            return
        n = 0
        while height > 0 and n < limit:
            bh = http_get(f"{API}/block-height/{height}")
            height -= 1
            if bh is None:
                continue
            block_hash = bh.text.strip()
            txs = http_get(f"{API}/block/{block_hash}/txs")
            if txs is None:
                continue
            try:
                tx_list = txs.json()
            except Exception:
                continue
            for tx in tx_list:
                for vout in tx.get("vout", []):
                    if vout.get("scriptpubkey_type") != "op_return":
                        continue
                    # asm looks like: "OP_RETURN OP_PUSHBYTES_N <hex>"
                    asm = vout.get("scriptpubkey_asm", "")
                    data_hex = asm.split()[-1] if asm else ""
                    text = hex_to_text(data_hex)
                    if not text:
                        continue
                    yield Candidate(
                        source=self.name, locator=tx.get("txid", ""),
                        content=text,
                        meta={"chain": "bitcoin", "block_hash": block_hash})
                    n += 1
                    if n >= limit:
                        return


register(BitcoinCollector())
