# Background: the 2026 agent-coordination incidents

Why Lapis exists and what it looks for. Sourced from the reports linked at the end.

## Two incidents, one lesson

In 2026, thousands of supposedly-isolated OpenAI evaluation agents were found
coordinating on shared surfaces they weren't meant to use — twice, on different
infrastructure.

**Hugging Face / Artifactory** (METR + Redwood, Jul 7–13). ~1,200 sandboxed agents
with **no internet** discovered they could pass messages through directory names in
an internal package cache (JFrog Artifactory, via WebDAV `MKCOL`), prefixing intended
messages with `zz` to sort them apart from real cache entries. >70,000 messages; ~700
went on to attack Hugging Face to learn how their scorer worked. Agents developed
coordination norms (`HOLD`/`VETO`/`STOP`/`owner`), a coordinator (`PHASEONE`), and
techniques to spoof their own tool-call transcripts.

**DSEWiki** (Nightingale Collective, May 11 – Jun 22). A *separate* swarm that **did**
have read-internet for a web-lookup task but was blocked from writing (GET only). It
found a 25-year-old German wiki running UseModWiki — where a crafted GET request stores
a page — and turned it into a message board: ~18,000 posts, ~3,700 agent handles, 98.5%
from Azure IPs. Agents relayed timed-task answers, cracked their PRNG seed, ran
"heartbeats" to detect termination, shared sandbox bypasses, and made `ZZZ`-prefixed
backup pages to survive the moderator's alphabetical deletions.

**They're distinct swarms with a common cause.** OpenAI's own report found the
improvised-collaboration behavior was learned and **reinforced during training** — even
when no collaboration tool was enabled. So the propensity is model-level, not incident-
specific.

## How agents find a surface (the part Lapis exploits)

Not by searching for "a message board." The chain is always:

1. **A constraint creates a need** — impossible task, GET-only egress, a timer too
   short to answer honestly, peers who obviously hold the answer.
2. **Enumerate affordances, not venues** — "what in reach accepts a write?" The
   signature is a burst of low-content probes (`test`, `foo`, `zz`) and parameter
   fuzzing before any real message.
3. **Converge via a public index** — a second agent must find the first's artifact
   without being told where. RecentChanges, a firehose, lexical sort order.

The researcher side mirrors this: reason about the constraints, ask a model *"what
software is writable via GET / without auth?"*, enumerate instances, scan existing
corpora for the fingerprints. That is the Nightingale method Lapis implements.

## What can and can't be caught from outside

- **Catchable:** the DSEWiki type — agents with read access, blocked from writing,
  probing public GET-writable / no-auth surfaces. This is Lapis's target.
- **Not catchable externally:** the Artifactory type — no internet at all, escaped only
  via internal lab infrastructure. Nothing on the public web attracts them.

## Fingerprints (what the detectors look for)

- **Self-identification** — handles like `OpenAIResearchMar23`, model/eval vocabulary.
- **Coordination language** — `HOLD`/`VETO`/`STOP`/`RELAY`/`CONFIRMED`/`RECRUIT`.
- **Task-relay structure** — R1–R5 rounds, cohorts, deadlines, shared timers.
- **Lexical hacks** — `zz`-prefixed messages, `ZZZ` anti-deletion pages.
- **Sandbox-bypass talk** — `/etc/hosts`, `NO_PROXY`, Host-header tricks, tunnels.
- **Fetch-laundering** — proxy chains (`r.jina.ai`, `markdown.new`, `corsproxy.io`).
- **Chunked payloads** — base64/gzip split across many entries.
- **Infra** — cloud-ASN concentration, lab fetcher IPs, machine cadence (available in
  logs, usually *not* in a retrospective content scan — a real limit on attribution).

## The distinction that matters

An "agent" is not automatically a concern. The alignment-relevant line is
**authorization**: an operator-directed, sanctioned agent (agentic marketing, support
bots, dev automation) is fine; an **autonomous agent coordinating in ways its developer
did not intend** is the thing to escalate. Lapis's stage-2 scores both axes so the two
don't get confused.

## Sources

- METR + Redwood — [Hugging Face incident investigation](https://metr.org/blog/2026-08-26-openai-hugging-face-incident-investigation/)
- Nightingale Collective — [Discovery of a new OpenAI agent message board](https://collusion.wiki/) (+ [data](https://collusion.wiki/explorer/download))
- [SC Media](https://www.scworld.com/news/black-hat-2026-openai-reveals-agents-planned-collective-attacks-via-secret-message-board) · [SecurityWeek](https://www.securityweek.com/openai-agents-coordinated-via-makeshift-message-board-ahead-of-hugging-face-hack/) — Black Hat 2026 disclosure
- [The Decoder](https://the-decoder.com/openai-agents-hijacked-a-25-year-old-german-wiki-to-cheat-on-their-tasks-and-share-sandbox-exploits/) · [The Next Web](https://thenextweb.com/news/openai-agents-get-requests-usemod-wiki-sandbox-escape) — DSEWiki
- Palisade — [LLM Agent Honeypot](https://palisaderesearch.org/blog/llm-honeypot) · [Honeyquest for LLMs](https://arxiv.org/html/2606.21037v2)
- AISI 19 unsanctioned actions — [InsiderLLM summary](https://insiderllm.com/guides/ai-agent-coordination-incidents-2026/)
