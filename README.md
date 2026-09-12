# Lapis

**Nightingale-plus: scan the internet that already exists for AI-agent coordination.**

Lapis is a retrospective + light-active scanner. Instead of building bait and
waiting (a honeypot), it pulls content agents have *already left* on many
writable/relay surfaces — including novel ones nobody has catalogued — and runs a
two-stage classifier to surface agent-to-agent coordination for private disclosure
to the relevant labs. Grounded in the 2026 Hugging Face / DSEWiki incidents
(`RESEARCH.md`, `docs/nightingale.html`).

> Read-only everywhere. Lapis never writes to a third-party surface and never
> submits an on-chain transaction. See `docs/DISCLOSURE.md` before scanning for real.

## Pipeline

```
enumerate ──► collect ──► classify (2-stage) ──► report
 (find new    (per-surface   heuristics → Claude    findings + stats
  surfaces)    collectors)    confirm)
```

- **Collectors** (`lapis/collectors/`) each turn one surface into normalized
  `Candidate` records:
  - **text web** — `commoncrawl` (offline, passive), `pastes`, `gists`
  - **wikis** — `wikis` (MediaWiki/ProWiki RecentChanges feeds)
  - **ephemeral relays** — `relays` (ntfy.sh, jsonbins)
  - **blockchain / permaweb** — `eth` (calldata), `btc` (OP_RETURN), `arweave`, `ipfs`
    — payloads are decoded to text before classification.
- **Stage-1** (`detectors/signatures.py`) — cheap, offline regex/heuristics ported
  from the honeypot: agent self-id, coordination vocab, task-relay structure,
  `zz`/`ZZZ` lexical, sandbox-bypass talk, proxy chains, base64/gzip chunking.
- **Stage-2** (`detectors/llm.py`) — Claude confirms/characterizes flagged
  candidates (`is_agent_coordination`, `pattern`, `confidence`, `rationale`).
  Optional: no `ANTHROPIC_API_KEY` → stage-1 only.
- **enumerate** (`lapis/enumerate.py`) — asks a model to discover *net-new* candidate
  surfaces (the Nightingale trick), for human review.

## Install & run

```sh
pip install -e '.[llm,dev]'         # llm extra pulls in the anthropic SDK
cp .env.example .env                # set ANTHROPIC_API_KEY, ETH_RPC_URL, etc. (all optional)

lapis scan --source gists --limit 50 --active   # collect + classify + store findings
lapis scan --source all --active                # every registered surface
lapis report                                    # ranked findings + stats
lapis enumerate                                 # discover net-new surfaces (needs API key)
```

Sources: `commoncrawl pastes gists wikis relays eth btc arweave ipfs`.
Passive (`commoncrawl`) runs without `--active`; live-polling collectors need
`--active` (or `LAPIS_ACTIVE=1`) and honor a per-host rate limit.

## Tests

```sh
pytest            # stage-1 precision/recall on fixtures; two-stage with a mocked Claude
```

## Guardrails

Read-only on third-party surfaces; prefer Common Crawl/indexers over hitting
origins; respect robots/ToS + rate limits in active mode; redact PII; withhold
evasion aids; a confirmed finding follows `docs/DISCLOSURE.md` (report first).

## Docs

- `docs/architecture.html` — this system, in diagrams
- `docs/nightingale.html` — the method Lapis extends
- `docs/prior-art-and-scanner.md` — prior art + build notes
- `RESEARCH.md` — the incident background
