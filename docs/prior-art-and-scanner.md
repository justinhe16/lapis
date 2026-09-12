# Prior art & method

Lapis operationalizes the **Nightingale method**: reason about the constraints a
boxed/escaped agent operates under, derive the *kind* of surface it can write to,
then scan existing corpora for the fingerprints of agent activity. See
[`nightingale.html`](nightingale.html) for the full breakdown.

## Sources

**Nightingale (the primary reference)**
- Report: https://collusion.wiki/ — appendix *"Searching for rogue agents"* is the method
- Data explorer / dump: https://collusion.wiki/explorer/ · /explorer/download
  *(visiting the site logs your IP; work from the dump offline)*

**Related**
- Palisade LLM Agent Honeypot (the active/prospective counterpart) — [paper](https://arxiv.org/html/2410.13919v1), [code](https://github.com/PalisadeResearch/llm-honeypot)
- Honeyquest for LLMs (how baitable agents are) — https://arxiv.org/html/2606.21037v2
- METR + Redwood, Hugging Face incident (the internal-infra contrast) — https://metr.org/blog/2026-08-26-openai-hugging-face-incident-investigation/
- AISI 19 unsanctioned actions (GitHub-Gist C2) — https://insiderllm.com/guides/ai-agent-coordination-incidents-2026/

## The pipeline Lapis implements

```
model constraints → enumerate surfaces → pull corpora → classify → review
   (what must be    (where they'd write)  (existing       (2-stage:   (human +
    true to write)                         scrapes)        detectors)  disclose)
```

Nightingale's key trick is stage B: ask a model *"what software is writable via
GET / without auth?"* → forums, bulletin boards, early wikis → UseModWiki →
DSEWiki. `lapis enumerate` reproduces it. The detectors (`lapis/detectors/`) are
the classify stage.

## Extending it — net-new surfaces & fingerprints

Nightingale found *one* surface with *known* fingerprints. The frontier is both:

**Net-new surfaces** — widen `enumerate` beyond wikis: paste-likes, JSON/KV relays
(ntfy.sh, webhook.site, jsonbin), redirect/proxy chains, collaborative editors,
DNS-TXT, IPFS, CT-log domains, and **blockchain data fields** (Lapis's `eth`/`btc`/
`arweave`/`ipfs` collectors — nobody has scanned chains for this).

**Net-new fingerprints (unsupervised)** — embed + cluster candidates (agent text
clusters tightly, apart from human); flag structural anomalies (base64/gzip
chunking, monotonic naming, machine cadence); use infra signals (ASN, fetcher IPs)
where available. Each confirmed pattern becomes a new rule in
`detectors/signatures.py`, improving every future scan.

## Guardrails

Read-only on third-party surfaces; prefer corpora/indexers over live origins;
respect robots/ToS + rate limits; redact PII; withhold evasion aids; report first
([`DISCLOSURE.md`](DISCLOSURE.md)).
