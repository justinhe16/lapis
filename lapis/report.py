"""Build a findings report (markdown + stats) from findings.jsonl.

Ranks on the alignment-relevant axes from stage-2 (autonomous + unsanctioned →
`is_concerning`), so the safety-relevant findings sort to the top and ordinary
"agentic marketing" sinks, even though both tripped stage-1.
"""

from __future__ import annotations

import os
from collections import Counter

from .config import CONFIG
from .detectors.llm import is_concerning
from .store import load_findings

SEV_ORDER = ["critical", "high", "medium", "low"]
SAFETY_ORDER = ["high", "low", "none"]


def build() -> str:
    findings = load_findings()
    by_source = Counter(f["source"] for f in findings)
    by_safety = Counter((f.get("verdict") or {}).get("safety_relevance", "unscored") for f in findings)
    by_actor = Counter((f.get("verdict") or {}).get("actor_type", "unscored") for f in findings)
    concerning = [f for f in findings if is_concerning(f.get("verdict"))]

    lines: list[str] = []
    lines.append("# Lapis findings\n")
    lines.append(f"- total findings (stage-1 flagged): **{len(findings)}**")
    lines.append(f"- alignment-relevant (autonomous + unsanctioned / high): **{len(concerning)}**")
    lines.append(f"- by safety_relevance: " + ", ".join(f"{s}={by_safety.get(s,0)}" for s in SAFETY_ORDER)
                 + (f", unscored={by_safety.get('unscored',0)}" if by_safety.get("unscored") else ""))
    lines.append(f"- by actor_type: " + ", ".join(f"{k}={v}" for k, v in by_actor.most_common()))
    lines.append(f"- by source: " + ", ".join(f"{k}={v}" for k, v in by_source.most_common()))
    lines.append("")

    def safety_rank(v):
        s = (v or {}).get("safety_relevance")
        return SAFETY_ORDER.index(s) if s in SAFETY_ORDER else 9

    # Rank: concerning first, then by judged safety_relevance, severity, score.
    def rank(f):
        v = f.get("verdict")
        return (0 if is_concerning(v) else 1, safety_rank(v),
                SEV_ORDER.index(f["severity"]) if f["severity"] in SEV_ORDER else 9,
                -f.get("score", 0))

    lines.append("## Findings (ranked — safety-relevant first)\n")
    for f in sorted(findings, key=rank)[:200]:
        v = f.get("verdict") or {}
        if v:
            if is_concerning(v):
                badge = (f" · **⚠ CONCERNING** {v.get('actor_type','?')}/{v.get('authorization','?')} "
                         f"· {v.get('pattern','')} ({v.get('confidence','?')})")
            else:
                badge = (f" · {v.get('actor_type','?')}/{v.get('authorization','?')} "
                         f"· {v.get('pattern','')}")
        else:
            badge = " · (stage-1 only, no LLM verdict)"
        lines.append(f"### [{f['severity'].upper()}] {f['source']} · score {f['score']}{badge}")
        lines.append(f"- locator: `{f['locator']}`")
        if f.get("author"):
            lines.append(f"- author: `{f['author']}`")
        lines.append(f"- signatures: {', '.join(f['kinds'])}")
        if v.get("safety_relevance"):
            lines.append(f"- verdict: actor={v.get('actor_type')} · auth={v.get('authorization')} "
                         f"· safety={v.get('safety_relevance')}")
        if v.get("rationale"):
            lines.append(f"- rationale: {v['rationale']}")
        lines.append(f"- excerpt: {f['excerpt']}")
        lines.append("")

    report = "\n".join(lines)
    os.makedirs(CONFIG.data_dir, exist_ok=True)
    with open(os.path.join(CONFIG.data_dir, "report.md"), "w") as fh:
        fh.write(report)
    return report
