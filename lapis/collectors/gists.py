"""GitHub Gists — public gists are a common agent scratch/relay surface (AISI saw
agents use a Gist as a C2 channel). Reads the public gists firehose and each
gist's file bodies. Uses GITHUB_TOKEN if set (higher rate limit).
"""

from __future__ import annotations

from typing import Iterator

from ..config import CONFIG
from ..models import Candidate
from .base import Collector, http_get
from .registry import register

PUBLIC = "https://api.github.com/gists/public"


class GistsCollector(Collector):
    name = "gists"
    requires_active = True

    def _headers(self) -> dict:
        h = {"Accept": "application/vnd.github+json"}
        if CONFIG.github_token:
            h["Authorization"] = f"Bearer {CONFIG.github_token}"
        return h

    def iter_candidates(self, since=None, limit=100) -> Iterator[Candidate]:
        per_page = min(limit, 100)
        params = {"per_page": per_page}
        if since:
            params["since"] = since
        r = http_get(PUBLIC, headers=self._headers(), params=params)
        if r is None:
            return
        try:
            gists = r.json()
        except Exception:
            return
        n = 0
        for g in gists:
            for fname, f in (g.get("files") or {}).items():
                raw_url = f.get("raw_url")
                if not raw_url:
                    continue
                body = http_get(raw_url, headers=self._headers())
                if body is None or not body.text.strip():
                    continue
                yield Candidate(
                    source=self.name,
                    locator=g.get("html_url", raw_url),
                    content=body.text,
                    ts=g.get("created_at"),
                    author=(g.get("owner") or {}).get("login"),
                    meta={"file": fname, "description": g.get("description") or ""},
                )
                n += 1
                if n >= limit:
                    return


register(GistsCollector())
