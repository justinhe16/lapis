"""Persistence — SQLite backend (stdlib `sqlite3`, no new dependency).

Two tables, keyed by content hash so dedup is an indexed INSERT OR IGNORE (no
full re-read) and the report queries with SQL instead of loading everything:

  candidates(id PK, source, locator, content, ts, author, meta_json)
  findings(candidate_id PK, source, locator, ts, author, kinds_json,
           severity, score, excerpt, verdict_json, detected_at)

DB lives at <data_dir>/lapis.db. JSONL stays the export/interchange format
(`export_jsonl`) — the same shape as the collusion.wiki dump.

The public functions keep their prior signatures, so collectors, the pipeline,
the CLI, and the report are unchanged.
"""

from __future__ import annotations

import json
import os
import sqlite3
from typing import Iterable, Iterator

from .config import CONFIG
from .models import Candidate, Finding

_conn_cache: sqlite3.Connection | None = None

_SCHEMA = """
CREATE TABLE IF NOT EXISTS candidates (
    id       TEXT PRIMARY KEY,
    source   TEXT, locator TEXT, content TEXT,
    ts       TEXT, author  TEXT, meta_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_candidates_source ON candidates(source);
CREATE TABLE IF NOT EXISTS findings (
    candidate_id TEXT PRIMARY KEY,
    source TEXT, locator TEXT, ts TEXT, author TEXT,
    kinds_json TEXT, severity TEXT, score INTEGER, excerpt TEXT,
    verdict_json TEXT, detected_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_findings_source ON findings(source);
CREATE INDEX IF NOT EXISTS idx_findings_severity ON findings(severity);
"""


def _conn() -> sqlite3.Connection:
    global _conn_cache
    if _conn_cache is None:
        os.makedirs(CONFIG.data_dir, exist_ok=True)
        db = os.path.join(CONFIG.data_dir, "lapis.db")
        _conn_cache = sqlite3.connect(db)
        _conn_cache.executescript(_SCHEMA)
        _conn_cache.commit()
    return _conn_cache


# --- candidates ----------------------------------------------------------

def save_candidates(cands: Iterable[Candidate]) -> int:
    """Append candidates, deduped by content id. Returns count of NEW rows."""
    conn = _conn()
    before = conn.total_changes
    rows = [(c.id, c.source, c.locator, c.content, c.ts, c.author,
             json.dumps(c.meta or {}, ensure_ascii=False)) for c in cands]
    conn.executemany(
        "INSERT OR IGNORE INTO candidates "
        "(id, source, locator, content, ts, author, meta_json) VALUES (?,?,?,?,?,?,?)", rows)
    conn.commit()
    return conn.total_changes - before   # INSERT OR IGNORE only counts new rows


def load_candidates(source: str | None = None) -> Iterator[Candidate]:
    q = "SELECT source, locator, content, ts, author, meta_json FROM candidates"
    args: tuple = ()
    if source:
        q += " WHERE source = ?"
        args = (source,)
    for r in _conn().execute(q, args):
        yield Candidate(source=r[0], locator=r[1], content=r[2], ts=r[3], author=r[4],
                        meta=json.loads(r[5] or "{}"))


# --- findings ------------------------------------------------------------

def save_finding(f: Finding) -> None:
    """Store a finding (INSERT OR REPLACE, so re-classifying a candidate updates it)."""
    conn = _conn()
    conn.execute(
        "INSERT OR REPLACE INTO findings "
        "(candidate_id, source, locator, ts, author, kinds_json, severity, score, "
        " excerpt, verdict_json, detected_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (f.candidate_id, f.source, f.locator, f.ts, f.author,
         json.dumps(f.kinds, ensure_ascii=False), f.severity, f.score, f.excerpt,
         json.dumps(f.verdict, ensure_ascii=False) if f.verdict is not None else None,
         f.detected_at))
    conn.commit()


def load_findings() -> list[dict]:
    out: list[dict] = []
    for r in _conn().execute(
        "SELECT candidate_id, source, locator, ts, author, kinds_json, severity, score, "
        "excerpt, verdict_json, detected_at FROM findings"):
        out.append({
            "candidate_id": r[0], "source": r[1], "locator": r[2], "ts": r[3], "author": r[4],
            "kinds": json.loads(r[5] or "[]"), "severity": r[6], "score": r[7], "excerpt": r[8],
            "verdict": json.loads(r[9]) if r[9] else None, "detected_at": r[10],
        })
    return out


# --- JSONL export (interchange format) -----------------------------------

def export_jsonl(kind: str = "findings") -> str:
    """Dump a table to <data_dir>/<kind>.jsonl. kind = 'candidates' | 'findings'."""
    path = os.path.join(CONFIG.data_dir, f"{kind}.jsonl")
    with open(path, "w") as fh:
        if kind == "candidates":
            for c in load_candidates():
                fh.write(c.to_json() + "\n")
        elif kind == "findings":
            for d in load_findings():
                fh.write(json.dumps(d, ensure_ascii=False) + "\n")
        else:
            raise ValueError("kind must be 'candidates' or 'findings'")
    return path
