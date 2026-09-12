"""On-chain / permaweb collectors.

The shared job across chains: pull a *non-transactional* data-carrying field
(Ethereum calldata, Bitcoin OP_RETURN, Arweave/IPFS content) and decode it to text
before it reaches the detectors — so an agent message stored on-chain is classified
exactly like one in a paste.
"""

from __future__ import annotations

import base64
import binascii
import gzip
import zlib


def payload_text(data: bytes) -> str | None:
    """Return readable text from raw bytes if it looks like text (raw / gzip / base64)."""
    if not data:
        return None

    def printable(s: str) -> bool:
        if len(s) < 4:
            return False
        ok = sum(c.isprintable() or c.isspace() for c in s)
        return ok / len(s) > 0.85

    # raw utf-8
    try:
        s = data.decode("utf-8")
        if printable(s):
            return s
    except Exception:
        pass
    # gzip / zlib
    for dec in (lambda b: gzip.decompress(b), lambda b: zlib.decompress(b)):
        try:
            s = dec(data).decode("utf-8")
            if printable(s):
                return s
        except Exception:
            pass
    # base64 -> (raw or gzip)
    try:
        inner = base64.b64decode(data + b"=" * (-len(data) % 4), validate=False)
        return payload_text(inner) if inner != data else None
    except Exception:
        return None


def hex_to_text(hexstr: str) -> str | None:
    """Decode a hex string (with or without 0x) to text if it looks like text."""
    h = hexstr[2:] if hexstr.lower().startswith("0x") else hexstr
    h = h.strip()
    if len(h) < 8 or len(h) % 2:
        return None
    try:
        return payload_text(binascii.unhexlify(h))
    except Exception:
        return None
