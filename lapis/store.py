"""Append-only, dependency-free persistence.

candidates.jsonl   — normalized content pulled by collectors (a cache)
findings.jsonl     — classified hits

Append-only is deliberate: this is an evidence record, and dedup is by content
id so re-running a collector never double-counts.
"""

from __future__ import annotations

import os
from typing import Iterable, Iterator

from .config import CONFIG
from .models import Candidate, Finding


def _path(name: str) -> str:
    os.makedirs(CONFIG.data_dir, exist_ok=True)
    return os.path.join(CONFIG.data_dir, name)


def save_candidates(cands: Iterable[Candidate]) -> int:
    """Append new candidates (deduped by content id). Returns count written."""
    path = _path("candidates.jsonl")
    existing = _existing_candidate_ids(path)
    n = 0
    with open(path, "a") as fh:
        for c in cands:
            if c.id in existing:
                continue
            fh.write(c.to_json() + "\n")
            existing.add(c.id)
            n += 1
    return n


def _existing_candidate_ids(path: str) -> set[str]:
    ids: set[str] = set()
    for c in load_candidates(path):
        ids.add(c.id)
    return ids


def load_candidates(path: str | None = None) -> Iterator[Candidate]:
    path = path or _path("candidates.jsonl")
    if not os.path.exists(path):
        return
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    yield Candidate.from_json(line)
                except Exception:
                    continue


def save_finding(f: Finding) -> None:
    with open(_path("findings.jsonl"), "a") as fh:
        fh.write(f.to_json() + "\n")


def load_findings() -> list[dict]:
    import json
    path = _path("findings.jsonl")
    out: list[dict] = []
    if not os.path.exists(path):
        return out
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except Exception:
                    continue
    return out
