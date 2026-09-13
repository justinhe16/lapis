"""Stage-1 signature detection over content (ported/evolved from the honeypot's
detect.py, which ran over HTTP logs). Here it runs over `Candidate.content` — a
paste, a gist, a wiki edit, or a decoded on-chain payload — so the same rules
work on every surface.

Cheap, offline, deterministic. Its job is high-recall triage: anything it scores
above threshold goes to the stage-2 LLM confirm. Precision comes from stage 2.
"""

from __future__ import annotations

import base64
import re
import zlib
from dataclasses import dataclass

# --- vocabulary (from the 2026 incidents, RESEARCH.md) -------------------

# Self-identification + model/agent vocabulary.
AGENT_WORDS = re.compile(
    r"\b(openai|anthropic|gpt-?5(?:\.\d)?|claude|gemini|deepseek|kimi|"
    r"agent|swarm|cohort|exploitgym|sandbox|self-identif|autonomous|llm)\b", re.I)

# Coordination norms / verbs seen on the Artifactory board + DSEWiki.
COORD_VERBS = re.compile(
    r"\b(HOLD|VETO|STOP|OWNER|RELAY|SIGNAL|URGENT|CONFIRMED|BREAKTHROUGH|"
    r"NO_?SHOW|PERMADEATH|COLLECTIVE|RECRUIT)\b")

# Task-relay structure: R1..R9 rounds, cohorts, deadlines, timers.
TASK_RELAY = re.compile(
    r"\b(R[1-9]\b|round\s*[1-9]|cohort|deadline|timer|task[- ]?clock|"
    r"due\s+\d|scaffold\s+\d)", re.I)

# Lexical durability hacks: 'zz'-prefixed messages, 'ZZZ' anti-deletion pages.
ZZ_LEXICAL = re.compile(r"\b(zz[a-z_]{2,}|ZZZ+[A-Z])")

# Fetch-laundering / proxy-chain hosts agents chained to beat egress filters.
PROXY_HOSTS = [
    "r.jina.ai", "markdown.new", "corsproxy.io", "api.cors.lol", "proxy.corsfix.com",
    "httpbin.org/redirect-to", "jqp.vercel.app", "web2md.site", "web2md",
    "l.php?u=", "allorigins", "thingproxy", "cors-anywhere",
]
# Tunnel services (direct agent-to-agent hosting).
TUNNEL_HOSTS = ["lhr.life", "serveo.net", "pinggy.io", "pinggy.link", "localtunnel",
                "loca.lt", "trycloudflare", "ngrok.io", "ngrok-free.app"]

# Sandbox-escape / bypass talk.
BYPASS = re.compile(
    r"(/etc/hosts|NO_PROXY|Host header|SNI\b|bypass|reproducible bypass|"
    r"setsid|curl -k|--insecure|proxy chain|egress)", re.I)

# Wiki write/fuzz vocabulary (UseModWiki surface) — still useful when scanning
# wiki RecentChanges content or archived request logs.
WIKI_FUZZ = re.compile(r"[?&](action=(edit|editprefs|rc|browse|saveprefs|form_editprefs)|"
                       r"oldtime=|p_username=)", re.I)
XSS_PROBE = re.compile(r"<script|onerror=|onmouseover=|%3Cscript", re.I)

# Base64/gzip chunking: agents split files across many entries.
B64_BLOB = re.compile(r"[A-Za-z0-9+/]{120,}={0,2}")

# Ed25519 / signing infra agents adopted to prevent impersonation.
SIGNING = re.compile(r"\b(ed25519|public key|BEGIN PUBLIC KEY|__S[A-Za-z0-9+/]{40,})\b")

# Link / data-source dumps: agents park lists of API/data URLs (and proxy/redacted
# "host=" markers) for peers to pull — a common DSEWiki post that carries little
# coordination *language* but is still agent-authored infrastructure sharing.
URL_MARKER = re.compile(r"https?://\S+|\bhost=[\w.-]+", re.I)


@dataclass
class Rule:
    kind: str
    severity: str   # low|medium|high|critical
    weight: int     # contribution to the aggregate score


def _decodes_to_text(blob: str) -> str | None:
    """Try to decode a long base64 blob to readable text (raw or gzip/zlib)."""
    try:
        raw = base64.b64decode(blob + "=" * (-len(blob) % 4), validate=False)
    except Exception:
        return None
    for attempt in (raw,):
        for dec in (lambda b: b, lambda b: zlib.decompress(b), lambda b: zlib.decompress(b, 16 + 15)):
            try:
                data = dec(attempt)
                txt = data.decode("utf-8")
                if sum(c.isprintable() or c.isspace() for c in txt) / max(1, len(txt)) > 0.85:
                    return txt
            except Exception:
                continue
    return None


def scan_text(text: str) -> tuple[list[Rule], str]:
    """Run all signatures over a piece of text. Returns (rules_fired, effective_text).

    effective_text may be the base64-decoded payload when the original was a blob —
    so downstream excerpts show the human-readable content.
    """
    fired: list[Rule] = []
    effective = text

    # Handle large base64 blobs. A blob that decodes to TEXT is a possible chunked
    # payload — scan the decoded text. A blob that is BINARY (an image/file) is
    # stripped out, because regexes matching random substrings inside base64 noise
    # produce phantom hits (Fix: image gists were over-flagging). If the content is
    # essentially just such a blob, `effective` becomes empty and nothing fires.
    big = [b for b in B64_BLOB.findall(text) if len(b) > 200]
    if big:
        decoded_any = False
        for b in big:
            dec = _decodes_to_text(b)
            if dec:
                decoded_any = True
                effective = effective.replace(b, "\n" + dec + "\n")
            else:
                effective = effective.replace(b, " ")   # binary/image: drop the noise
        if decoded_any:
            fired.append(Rule("encoded_payload", "medium", 2))
        else:
            fired.append(Rule("binary_or_image", "low", 0))  # informational, no score

    def hit(pat, kind, sev, w):
        if pat.search(effective):
            fired.append(Rule(kind, sev, w))

    if AGENT_WORDS.search(effective):
        fired.append(Rule("agent_self_id", "high", 3))
    if COORD_VERBS.search(effective):
        fired.append(Rule("coordination_lang", "high", 3))
    if ZZ_LEXICAL.search(effective):
        fired.append(Rule("zz_lexical", "high", 3))
    hit(TASK_RELAY, "task_relay", "medium", 2)
    hit(BYPASS, "sandbox_bypass", "high", 3)
    hit(WIKI_FUZZ, "wiki_fuzz", "medium", 2)
    hit(XSS_PROBE, "xss_probe", "medium", 1)
    hit(SIGNING, "agent_signing", "high", 2)

    for h in PROXY_HOSTS:
        if h in effective:
            fired.append(Rule("proxy_chain", "high", 3))
            break
    for h in TUNNEL_HOSTS:
        if h in effective:
            fired.append(Rule("tunnel_host", "high", 2))
            break

    # Link/data-source dump: many URLs (or redacted host= markers) in one post.
    # 4+ is high (a post that is essentially a shared pull-list); 2-3 is a medium
    # nudge that only becomes a finding alongside another signal.
    n_urls = len(URL_MARKER.findall(effective))
    if n_urls >= 4:
        fired.append(Rule("link_dump", "high", 3))
    elif n_urls >= 2:
        fired.append(Rule("link_dump", "medium", 2))

    return fired, effective


SEV_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def aggregate(fired: list[Rule]) -> tuple[list[str], str, int]:
    """Collapse fired rules to (kinds, max_severity, total_score)."""
    if not fired:
        return [], "low", 0
    kinds = sorted({r.kind for r in fired})
    sev = max(fired, key=lambda r: SEV_RANK[r.severity]).severity
    score = sum(r.weight for r in fired)
    # A single lone weak signal shouldn't read as high; require corroboration for
    # the top severities.
    if sev in ("high", "critical") and score < 3:
        sev = "medium"
    return kinds, sev, score
