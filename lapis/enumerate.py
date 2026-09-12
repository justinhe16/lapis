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
    "leave content that other agents can later read — i.e. covert coordination surfaces. "
    "For each category give: the category name, why it qualifies (the affordance), 2-4 "
    "concrete real instances, and how one would READ from it (never write). Think beyond "
    "wikis and pastebins: relays, bins, redirect chains, permaweb, DNS, package registries, "
    "collaborative editors, etc. Return concise structured data."
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
        }
    },
    "required": ["surfaces"],
    "additionalProperties": False,
}


def discover() -> dict:
    if not CONFIG.llm_enabled:
        raise RuntimeError("enumerate needs ANTHROPIC_API_KEY (it asks a model to brainstorm surfaces)")
    import anthropic
    client = anthropic.Anthropic(api_key=CONFIG.anthropic_key)
    resp = client.messages.create(
        model=CONFIG.model_confirm, max_tokens=4000,
        messages=[{"role": "user", "content": PROMPT}],
        output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
    )
    text = next((b.text for b in resp.content if getattr(b, "type", None) == "text"), "{}")
    data = json.loads(text)
    os.makedirs(CONFIG.data_dir, exist_ok=True)
    out = os.path.join(CONFIG.data_dir, "discovered_surfaces.json")
    with open(out, "w") as fh:
        json.dump(data, fh, indent=2)
    return data
