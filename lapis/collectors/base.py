"""Collector framework.

A Collector turns one surface (pastes, gists, a chain, ...) into a stream of
normalized `Candidate`s. Collectors never classify — they just fetch and normalize.

Acquisition modes (RESEARCH.md / plan):
  passive  — offline corpora + historical indexers only (no live third-party origins)
  active   — adds read-only polling of public feeds/APIs, rate-limited, UA-identified

Each collector declares `requires_active`; the runner skips active collectors when
the user runs in passive mode.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Iterator, Optional
from urllib.parse import urlparse

from ..config import CONFIG
from ..models import Candidate

# Lazy import so the package imports without requests installed (tests don't need it).
try:
    import requests  # type: ignore
except Exception:  # pragma: no cover
    requests = None  # type: ignore

_last_hit: dict[str, float] = defaultdict(float)


def _throttle(url: str) -> None:
    """Simple per-host rate limit for polite, read-only polling."""
    host = urlparse(url).netloc
    gap = 1.0 / max(CONFIG.rate_per_host, 0.01)
    wait = gap - (time.time() - _last_hit[host])
    if wait > 0:
        time.sleep(wait)
    _last_hit[host] = time.time()


def http_get(url: str, *, headers: dict | None = None, params: dict | None = None,
             timeout: int = 20) -> "Optional[requests.Response]":
    """Rate-limited, UA-identified GET. Returns None on any failure (never raises)."""
    if requests is None:
        raise RuntimeError("the 'requests' package is required for network collectors")
    _throttle(url)
    h = {"User-Agent": CONFIG.user_agent}
    if headers:
        h.update(headers)
    try:
        r = requests.get(url, headers=h, params=params, timeout=timeout)
        if r.status_code == 200:
            return r
        return None
    except Exception:
        return None


class Collector(ABC):
    name: str = "base"
    requires_active: bool = True   # most collectors touch live APIs

    @abstractmethod
    def iter_candidates(self, since: str | None = None, limit: int = 100) -> Iterator[Candidate]:
        ...
