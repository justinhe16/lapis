"""Collector registry. Discovered surfaces (from enumerate.py) can register here
too, so `lapis scan --source <name>` works for built-in and discovered collectors
alike.
"""

from __future__ import annotations

from typing import Iterator

from ..models import Candidate
from .base import Collector

_REGISTRY: dict[str, Collector] = {}


def register(collector: Collector) -> Collector:
    _REGISTRY[collector.name] = collector
    return collector


def get(name: str) -> Collector | None:
    _ensure_loaded()
    return _REGISTRY.get(name)


def names() -> list[str]:
    _ensure_loaded()
    return sorted(_REGISTRY)


def all_collectors() -> list[Collector]:
    _ensure_loaded()
    return [_REGISTRY[n] for n in names()]


_loaded = False


def _ensure_loaded() -> None:
    """Import built-in collector modules once; each registers itself on import."""
    global _loaded
    if _loaded:
        return
    _loaded = True
    from . import pastes, gists, commoncrawl, wikis, relays, dump    # noqa: F401
    from .chains import ethereum, bitcoin, arweave, ipfs             # noqa: F401


def collect(source: str, since: str | None, limit: int, active: bool) -> Iterator[Candidate]:
    """Yield candidates from one source, honoring the passive/active gate."""
    c = get(source)
    if c is None:
        raise KeyError(f"unknown source '{source}'. known: {', '.join(names())}")
    if c.requires_active and not active:
        raise PermissionError(
            f"source '{source}' needs active mode (read-only live polling). "
            f"Set LAPIS_ACTIVE=1 or pass --active.")
    yield from c.iter_candidates(since=since, limit=limit)
