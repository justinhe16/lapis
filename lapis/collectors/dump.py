"""Local dump collector — read a corpus you already downloaded (e.g. the
collusion.wiki DSEWiki dump) into Candidates, for validating the detectors against
known data. Passive: reads local files only, no network.

Point it at a directory:  LAPIS_DUMP_DIR (default: data/dump)
Handles:
  .jsonl / .json  — one Candidate per record (maps common field names)
  .html/.htm      — tags stripped, one Candidate per file
  .txt/.md/others — one Candidate per file
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Iterator

from ..models import Candidate
from .base import Collector
from .registry import register

DUMP_DIR = os.environ.get("LAPIS_DUMP_DIR", os.path.join(os.environ.get("LAPIS_DATA_DIR", "data"), "dump"))

_TAGS = re.compile(r"<[^>]+>")


def _pick(d: dict, keys: list[str]) -> Any:
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return None


def _candidate_from_record(rec: dict, locator_hint: str) -> Candidate | None:
    content = _pick(rec, ["content", "text", "body", "message", "wikitext", "revision"])
    if not content:
        return None
    return Candidate(
        source="dump",
        locator=str(_pick(rec, ["url", "locator", "page", "title", "id"]) or locator_hint),
        content=str(content),
        ts=_pick(rec, ["ts", "timestamp", "time", "date", "created_at"]),
        author=_pick(rec, ["author", "user", "username", "name", "handle"]),
        meta={"dump_file": os.path.basename(locator_hint),
              **{k: rec[k] for k in ("title", "wiki", "site") if k in rec}},
    )


class DumpCollector(Collector):
    name = "dump"
    requires_active = False   # local files only

    def iter_candidates(self, since=None, limit=100) -> Iterator[Candidate]:
        if not os.path.isdir(DUMP_DIR):
            return
        n = 0
        for root, _, files in os.walk(DUMP_DIR):
            for fname in sorted(files):
                path = os.path.join(root, fname)
                lower = fname.lower()
                try:
                    if lower.endswith(".jsonl"):
                        with open(path, encoding="utf-8", errors="replace") as fh:
                            for i, line in enumerate(fh):
                                line = line.strip()
                                if not line:
                                    continue
                                try:
                                    rec = json.loads(line)
                                except Exception:
                                    continue
                                c = _candidate_from_record(rec, f"{path}#{i}")
                                if c:
                                    yield c
                                    n += 1
                                    if n >= limit:
                                        return
                    elif lower.endswith(".json"):
                        with open(path, encoding="utf-8", errors="replace") as fh:
                            data = json.load(fh)
                        records = data if isinstance(data, list) else data.get("records", data.get("pages", []))
                        for i, rec in enumerate(records if isinstance(records, list) else []):
                            if not isinstance(rec, dict):
                                continue
                            c = _candidate_from_record(rec, f"{path}#{i}")
                            if c:
                                yield c
                                n += 1
                                if n >= limit:
                                    return
                    else:
                        with open(path, encoding="utf-8", errors="replace") as fh:
                            text = fh.read()
                        if lower.endswith((".html", ".htm")):
                            text = _TAGS.sub(" ", text)
                        if text.strip():
                            yield Candidate(source="dump", locator=path, content=text,
                                            meta={"dump_file": fname})
                            n += 1
                            if n >= limit:
                                return
                except Exception:
                    continue


register(DumpCollector())
