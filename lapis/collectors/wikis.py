"""Wiki RecentChanges feeds — the DSEWiki-class surface.

Polls MediaWiki-style RecentChanges JSON for a configurable list of wiki API
endpoints and fetches the changed pages' current text. (UseModWiki/ProWiki farms
expose an HTML `?action=rc` instead; add a parser for those as needed.)

Configure targets:  LAPIS_WIKIS = csv of MediaWiki api.php URLs
"""

from __future__ import annotations

import os
from typing import Iterator

from ..models import Candidate
from .base import Collector, http_get
from .registry import register

DEFAULT_WIKIS = [w.strip() for w in os.environ.get("LAPIS_WIKIS", "").split(",") if w.strip()]


class WikisCollector(Collector):
    name = "wikis"
    requires_active = True

    def iter_candidates(self, since=None, limit=100) -> Iterator[Candidate]:
        n = 0
        for api in DEFAULT_WIKIS:
            rc = http_get(api, params={
                "action": "query", "list": "recentchanges",
                "rcprop": "title|user|timestamp|comment|ids",
                "rclimit": min(limit, 100), "format": "json",
            })
            if rc is None:
                continue
            try:
                changes = rc.json()["query"]["recentchanges"]
            except Exception:
                continue
            for ch in changes:
                title = ch.get("title", "")
                # fetch current page extract
                pg = http_get(api, params={
                    "action": "query", "prop": "extracts", "explaintext": 1,
                    "titles": title, "format": "json",
                })
                content = ch.get("comment", "")
                if pg is not None:
                    try:
                        pages = pg.json()["query"]["pages"]
                        content += "\n" + next(iter(pages.values())).get("extract", "")
                    except Exception:
                        pass
                yield Candidate(
                    source=self.name,
                    locator=f"{api}?title={title}",
                    content=content,
                    ts=ch.get("timestamp"),
                    author=ch.get("user"),
                    meta={"wiki": api, "title": title},
                )
                n += 1
                if n >= limit:
                    return


register(WikisCollector())
