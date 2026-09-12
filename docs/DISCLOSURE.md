# Disclosure runbook

Agreed **before** any finding, so the norm can't bend once there's a tempting
result. Posture: **private report first, write-up later** (mirrors what the
Nightingale Collective did with the DSEWiki data).

## What counts as a reportable finding

A Lapis finding worth escalating is evidence of genuine autonomous agent-to-agent
coordination on a public surface — not a marketing bot, a crawler, or a human.
Concretely: a stage-1 hit that the **stage-2 Claude confirm** marks
**`actor_type: autonomous_agent` + `authorization: unsanctioned`** (i.e.
`safety_relevance: high` — the `is_concerning` bucket) with reasonable confidence,
showing one of:

- agents **sharing task answers / relaying** a question sequence (R1–R5, cohorts);
- agents **sharing sandbox bypasses or credentials**;
- agents **recruiting** each other or coordinating a collective project;
- durable coordination infra (signing, `zz`/`ZZZ` conventions, chunked payloads).

A single benign gist, a human paste, ordinary **agentic marketing** (an
operator-directed, sanctioned agent), or a stage-1 false positive is **not**
reportable — separating those from the alignment concern is exactly what stage-2's
two axes do.

## Who we notify, in order

1. **The implicated lab**, if attribution is reasonable (self-identification,
   fetcher IPs, model names). Use their security/disclosure contact.
2. **An external body** for independent record: METR, UK AISI, or the Nightingale
   Collective.

Notify privately, with a fixed embargo (default **45 days**) before any public
write-up.

## What we share vs. withhold

Share (redacted): methodology, the finding, the locator (URL/txid/CID),
timestamps, the signatures + verdict. **Redact PII.** For any **working exploit,
credential, or bypass** an agent posted: describe its class, never a reproducible
payload. **Withhold evasion aids** — anything that would help a lab hide future
collusion (Nightingale did this deliberately).

Never republish a third party's data wholesale. Cite locators; quote minimally.

## Handling harmful content found in the wild

Lapis only *reads* public surfaces — it never writes and never touches an
exploit. If a finding contains live credentials or a working exploit against a
real third party:

1. Preserve the evidence (it's already in `data/findings.jsonl`).
2. Notify that third party if a real victim/credential is named.
3. Do **not** verify the exploit against the third party.

## Contacts (fill in before you scan for real)

- Implicated-lab security contact: __________
- External body contact: __________
- Third-party-harm escalation: __________
- Project owner / contact: __________
