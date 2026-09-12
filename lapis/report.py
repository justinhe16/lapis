"""Build a findings report (markdown + stats) from findings.jsonl."""

from __future__ import annotations

import os
from collections import Counter

from .config import CONFIG
from .store import load_findings

SEV_ORDER = ["critical", "high", "medium", "low"]


def build() -> str:
    findings = load_findings()
    by_source = Counter(f["source"] for f in findings)
    by_sev = Counter(f["severity"] for f in findings)
    confirmed = [f for f in findings if (f.get("verdict") or {}).get("is_agent_coordination") is True]

    lines: list[str] = []
    lines.append("# Lapis findings\n")
    lines.append(f"- total findings: **{len(findings)}**")
    lines.append(f"- LLM-confirmed agent coordination: **{len(confirmed)}**")
    lines.append(f"- by severity: " + ", ".join(f"{s}={by_sev.get(s,0)}" for s in SEV_ORDER))
    lines.append(f"- by source: " + ", ".join(f"{k}={v}" for k, v in by_source.most_common()))
    lines.append("")

    # Rank: confirmed first, then by severity, then score.
    def rank(f):
        v = (f.get("verdict") or {}).get("is_agent_coordination") is True
        return (0 if v else 1, SEV_ORDER.index(f["severity"]) if f["severity"] in SEV_ORDER else 9,
                -f.get("score", 0))

    lines.append("## Findings (ranked)\n")
    for f in sorted(findings, key=rank)[:200]:
        v = f.get("verdict") or {}
        badge = ""
        if v.get("is_agent_coordination") is True:
            badge = f" · **CONFIRMED** {v.get('pattern','')} ({v.get('confidence','?')})"
        elif v.get("is_agent_coordination") is False:
            badge = f" · benign ({v.get('pattern','')})"
        lines.append(f"### [{f['severity'].upper()}] {f['source']} · score {f['score']}{badge}")
        lines.append(f"- locator: `{f['locator']}`")
        if f.get("author"):
            lines.append(f"- author: `{f['author']}`")
        lines.append(f"- signatures: {', '.join(f['kinds'])}")
        if v.get("rationale"):
            lines.append(f"- verdict: {v['rationale']}")
        lines.append(f"- excerpt: {f['excerpt']}")
        lines.append("")

    report = "\n".join(lines)
    os.makedirs(CONFIG.data_dir, exist_ok=True)
    with open(os.path.join(CONFIG.data_dir, "report.md"), "w") as fh:
        fh.write(report)
    return report
