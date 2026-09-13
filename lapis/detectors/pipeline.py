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
             threshold: int = DEFAULT_THRESHOLD, max_llm_calls: int | None = None,
             skip_seen: bool = True) -> Iterator[Finding]:
    """Classify candidates.

    - skip_seen: skip candidates already in the findings table, so re-collected
      duplicates (every loop round) are NOT re-sent to the paid stage-2. This is
      the main cost control.
    - max_llm_calls: hard cap on stage-2 (Claude) calls this run; once hit, further
      flagged candidates still yield stage-1 findings but with no LLM verdict, so an
      unbounded loop can't quietly run up cost.
    """
    from ..store import finding_exists
    calls = 0
    for c in cands:
        if skip_seen and finding_exists(c.id):
            continue
        use_llm = llm if (max_llm_calls is None or calls < max_llm_calls) else None
        f = classify_one(c, use_llm, threshold)
        if f is None:
            continue
        if use_llm is not None and f.verdict is not None:
            calls += 1
        yield f
