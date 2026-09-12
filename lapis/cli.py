"""Lapis CLI:  lapis enumerate | collect | scan | report

  enumerate                 discover net-new candidate surfaces (needs ANTHROPIC_API_KEY)
  collect  --source S       pull candidates from surface S into the cache
  scan     --source S       collect + classify (heuristics -> Claude) + store findings
  report                    build a findings report from findings.jsonl
"""

from __future__ import annotations

import argparse
import sys

from .config import CONFIG
from .collectors import registry
from .detectors.llm import get_client
from .detectors.pipeline import classify, DEFAULT_THRESHOLD
from .store import save_candidates, save_finding


def _sources_arg(p):
    p.add_argument("--source", required=True, help=f"one of: {', '.join(registry.names())} (or 'all')")
    p.add_argument("--limit", type=int, default=100)
    p.add_argument("--active", action="store_true", help="allow read-only live polling")


def _iter_sources(source, active, limit):
    names = registry.names() if source == "all" else [source]
    for name in names:
        c = registry.get(name)
        if c is None:
            print(f"! unknown source: {name}", file=sys.stderr)
            continue
        if c.requires_active and not (active or CONFIG.active):
            print(f"~ skipping '{name}' (needs --active / LAPIS_ACTIVE=1)", file=sys.stderr)
            continue
        yield from c.iter_candidates(limit=limit)


def cmd_collect(args):
    cands = list(_iter_sources(args.source, args.active, args.limit))
    n = save_candidates(cands)
    print(f"collected {len(cands)} candidate(s), {n} new -> {CONFIG.data_dir}/candidates.jsonl")


def cmd_scan(args):
    llm = get_client()
    print(f"stage-2 classifier: {'Claude ' + CONFIG.model_confirm if llm else 'DISABLED (no ANTHROPIC_API_KEY) — heuristics only'}")
    cands = _iter_sources(args.source, args.active, args.limit)
    saved = list(cands)
    save_candidates(saved)
    hits = 0
    for f in classify(saved, llm, threshold=args.threshold):
        save_finding(f)
        v = (f.verdict or {}).get("is_agent_coordination")
        tag = "CONFIRMED" if v is True else ("benign" if v is False else "flagged")
        print(f"[{f.severity.upper():8}] {f.source:11} {tag:9} {', '.join(f.kinds)} :: {f.locator}")
        hits += 1
    print(f"-- {len(saved)} scanned, {hits} finding(s) -> {CONFIG.data_dir}/findings.jsonl")


def cmd_report(args):
    from .report import build
    print(build())


def cmd_enumerate(args):
    from .enumerate import discover
    data = discover()
    for s in data.get("surfaces", []):
        print(f"* {s['category']}: {s['affordance']}")
        print(f"    instances: {', '.join(s.get('instances', []))}")
        print(f"    read via:  {s.get('read_method','')}")
    print(f"-> saved {CONFIG.data_dir}/discovered_surfaces.json")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="lapis", description="Nightingale-plus agent-fingerprint scanner")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("collect", help="pull candidates from a surface"); _sources_arg(p)
    p.set_defaults(fn=cmd_collect)

    p = sub.add_parser("scan", help="collect + classify + store findings"); _sources_arg(p)
    p.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD)
    p.set_defaults(fn=cmd_scan)

    p = sub.add_parser("report", help="build a findings report"); p.set_defaults(fn=cmd_report)
    p = sub.add_parser("enumerate", help="discover net-new surfaces"); p.set_defaults(fn=cmd_enumerate)

    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
