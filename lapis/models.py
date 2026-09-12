"""Normalized records that flow through Lapis.

Every collector, whatever surface it reads (a paste, a gist, a wiki edit, an
on-chain payload), yields the same `Candidate`. The detectors and the report
only ever see `Candidate` / `Finding`, so adding a new surface never touches the
classifier.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from typing import Any


def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Candidate:
    """One piece of already-existing content to be scanned for agent traces."""
    source: str                      # collector name: "pastes", "gists", "eth", ...
    locator: str                     # stable id: URL, txid, CID — where to find it again
    content: str                     # decoded text (chains decode payload before this)
    ts: str | None = None            # ISO timestamp of the content, if known
    author: str | None = None        # handle/username/address, if any
    meta: dict[str, Any] = field(default_factory=dict)  # anything surface-specific

    @property
    def id(self) -> str:
        """Deterministic id for dedup/caching: source + locator + content hash."""
        h = hashlib.sha256(f"{self.source}\x00{self.locator}\x00{self.content}".encode()).hexdigest()
        return h[:16]

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    @staticmethod
    def from_json(line: str) -> "Candidate":
        d = json.loads(line)
        return Candidate(**d)


@dataclass
class Finding:
    """A classified hit. Stage-1 fills kinds/severity/score; stage-2 fills verdict."""
    candidate_id: str
    source: str
    locator: str
    ts: str | None
    author: str | None
    kinds: list[str]                 # stage-1 signature names that fired
    severity: str                    # max stage-1 severity: low|medium|high|critical
    score: int                       # stage-1 heuristic score
    excerpt: str                     # short snippet for the report
    # stage-2 (Claude) — None until/unless the LLM confirm runs:
    verdict: dict[str, Any] | None = None   # {is_agent_coordination, pattern, confidence, rationale}
    detected_at: str = field(default_factory=_now)

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


# Severity ordering shared across the codebase.
SEVERITY = {"low": 0, "medium": 1, "high": 2, "critical": 3}
