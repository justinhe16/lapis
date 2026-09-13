"""Bridge between `enumerate` and the collectors.

`lapis enumerate` asks a model where agents could coordinate and writes
`data/discovered_surfaces.json`. Collectors call `targets(<key>)` here to fold
those machine-usable target lists into what they scan — so the candidate set
grows over time instead of being hardcoded.

Keys: 'commoncrawl_patterns', 'wikis_apis', 'ntfy_topics'.
"""

from __future__ import annotations

import json
import os

from .config import CONFIG


def _load() -> dict:
    p = os.path.join(CONFIG.data_dir, "discovered_surfaces.json")
    if os.path.exists(p):
        try:
            return json.load(open(p))
        except Exception:
            return {}
    return {}


def targets(key: str) -> list[str]:
    vals = (_load().get("targets") or {}).get(key, [])
    # de-dupe, keep order, drop blanks/non-strings
    seen, out = set(), []
    for v in vals if isinstance(vals, list) else []:
        if isinstance(v, str) and v.strip() and v not in seen:
            seen.add(v); out.append(v.strip())
    return out
