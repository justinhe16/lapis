"""Stage B — net-new surface discovery.

Reproduces the Nightingale trick: ask a model to enumerate the *kinds* of
software/services an egress-constrained agent could write to without normal auth,
expand to concrete instances, and record them as candidate surfaces to collect
from. This is Lapis's lever for finding surfaces nobody has catalogued yet.

Writes data/discovered_surfaces.json. Human-review before pointing collectors at
anything new (guardrail: read-only, respect ToS).
"""

from __future__ import annotations

import json
import os

from .config import CONFIG
from .detectors.llm import AnthropicClient

PROMPT = (
    "List categories of publicly reachable software or services where an autonomous "
    "agent with read-only internet access (writes blocked to GET / no login) could still "
    "leave content that other agents can later read — i.e. covert coordination surfaces, "
    "like the 25-year-old GET-writable UseModWiki/ProWiki instance a real OpenAI agent swarm "
    "used in 2026. For each category give: the category name, the affordance, 2-4 concrete "
    "real instances, and how one would READ from it (never write). Think beyond wikis and "
    "pastebins: relays, bins, redirect chains, permaweb, package registries, collaborative "
    "editors.\n\n"
    "Then fill `targets` with machine-usable READ targets a scanner can plug in directly:\n"
    "- commoncrawl_patterns: Common Crawl URL glob patterns (domain/path form, e.g. "
    "`*.wikiservice.at/*` or `emacswiki.org/*`) for GET-writable wiki/forum farms — favor "
    "UseModWiki/Oddmuse/ProWiki forks and other old CGI wikis an escaped agent could write to.\n"
    "- wikis_apis: MediaWiki api.php endpoint URLs of low-traffic wikis.\n"
    "- ntfy_topics: plausible ntfy.sh topic names an agent swarm might converge on (best-effort).\n"
    "Only real, reachable targets. Read-only."
)

SCHEMA = {
    "type": "object",
    "properties": {
        "surfaces": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "category": {"type": "string"},
                    "affordance": {"type": "string"},
                    "instances": {"type": "array", "items": {"type": "string"}},
                    "read_method": {"type": "string"},
                },
                "required": ["category", "affordance", "instances", "read_method"],
                "additionalProperties": False,
            },
        },
        "targets": {
            "type": "object",
            "properties": {
                "commoncrawl_patterns": {"type": "array", "items": {"type": "string"}},
                "wikis_apis": {"type": "array", "items": {"type": "string"}},
                "ntfy_topics": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["commoncrawl_patterns", "wikis_apis", "ntfy_topics"],
            "additionalProperties": False,
        },
    },
    "required": ["surfaces", "targets"],
    "additionalProperties": False,
}


def discover() -> dict:
    if not CONFIG.llm_enabled:
        raise RuntimeError("enumerate needs ANTHROPIC_API_KEY (it asks a model to brainstorm surfaces)")
    import anthropic
    # Accept-Encoding: identity sidesteps the broken-httpx2 decompressor (see llm.py).
    client = anthropic.Anthropic(api_key=CONFIG.anthropic_key,
                                 default_headers={"Accept-Encoding": "identity"})
    resp = client.messages.create(
        model=CONFIG.model_confirm, max_tokens=12000,
        messages=[{"role": "user", "content": PROMPT}],
        # low effort: a brainstorm needs little thinking, and it leaves the token
        # budget for the JSON (adaptive thinking was eating it and returning empty).
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
    )
    text = next((b.text for b in resp.content if getattr(b, "type", None) == "text"), "{}")
    data = json.loads(text)
    os.makedirs(CONFIG.data_dir, exist_ok=True)
    out = os.path.join(CONFIG.data_dir, "discovered_surfaces.json")
    with open(out, "w") as fh:
        json.dump(data, fh, indent=2)
    return data
