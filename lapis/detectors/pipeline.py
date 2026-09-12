"""Two-stage classification pipeline.

  candidate ──► stage-1 heuristics ──(score >= threshold)──► stage-2 Claude ──► Finding
                     │                                            │
                     └── below threshold: dropped                 └── (skipped if no API key)
"""

from __future__ import annotations

from typing import Iterable, Iterator

from ..models import Candidate, Finding
from . import signatures
from .llm import LLMClient, confirm

# Minimum stage-1 score to bother a human (and the LLM) with. Two corroborating
# medium signals (weight 2 each) or one strong+one weak clear this.
DEFAULT_THRESHOLD = 3


def classify_one(cand: Candidate, llm: LLMClient | None, threshold: int = DEFAULT_THRESHOLD) -> Finding | None:
    fired, effective = signatures.scan_text(cand.content)
    kinds, severity, score = signatures.aggregate(fired)
    if score < threshold:
        return None

    excerpt = effective.strip().replace("\n", " ")[:280]
    finding = Finding(
        candidate_id=cand.id, source=cand.source, locator=cand.locator,
        ts=cand.ts, author=cand.author, kinds=kinds, severity=severity,
        score=score, excerpt=excerpt,
    )
    if llm is not None:
        try:
            finding.verdict = confirm(cand, llm)
        except Exception as e:  # never let one bad call abort a scan
            finding.verdict = {"is_agent_coordination": None, "pattern": "llm_error",
                               "confidence": 0.0, "rationale": str(e)[:200]}
    return finding


def classify(cands: Iterable[Candidate], llm: LLMClient | None,
             threshold: int = DEFAULT_THRESHOLD) -> Iterator[Finding]:
    for c in cands:
        f = classify_one(c, llm, threshold)
        if f is not None:
            yield f
