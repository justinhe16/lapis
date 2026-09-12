# Lapis

Scan the public internet for traces of **AI agents coordinating** — the way the
2026 Hugging Face and DSEWiki incidents were found *after the fact*, not with bait.

Lapis pulls content agents may already have left across many writable surfaces —
pastes, gists, Common Crawl, wikis, ephemeral relays, and **blockchain / permaweb** —
and runs a two-stage classifier to separate genuine unsanctioned agent coordination
from humans and ordinary bots. Background: [`docs/nightingale.html`](docs/nightingale.html),
[`RESEARCH.md`](RESEARCH.md).

> **Read-only.** Lapis never writes to a third-party surface and never sends a
> transaction. It is defensive research — see **Intended use** below and
> [`docs/DISCLOSURE.md`](docs/DISCLOSURE.md).

## How it works

```
enumerate ─► collect ─► classify ─► report
 find new    per-surface  stage-1 heuristics → stage-2 Claude   ranked findings
 surfaces    collectors   (recall)             (precision)
```

- **Collect** (`lapis/collectors/`) — nine surfaces, each yielding one normalized
  `Candidate`: `commoncrawl` (passive), `pastes`, `gists`, `wikis`, `relays`, and
  chains `eth` / `btc` / `arweave` / `ipfs` (payloads decoded to text first).
- **Stage-1** (`detectors/signatures.py`) — offline regex/heuristics: agent self-id,
  coordination verbs, task-relay, `zz`/`ZZZ`, sandbox-bypass, proxy chains, base64/gzip.
  High recall; it triages, it doesn't judge.
- **Stage-2** (`detectors/llm.py`) — Claude scores two axes: **actor** (human /
  operator-directed agent / autonomous agent) and **authorization** (sanctioned /
  unsanctioned). Only *autonomous + unsanctioned* is `safety_relevance: high` — so
  agentic marketing sinks and real collusion surfaces. Optional; without a key, stage-1 only.
- **enumerate** (`lapis/enumerate.py`) — asks a model for *net-new* surfaces to scan.

## Use

```sh
pip install -e '.[llm,dev]'
cp .env.example .env          # optional: ANTHROPIC_API_KEY, ETH_RPC_URL, GITHUB_TOKEN

lapis scan --source gists --limit 50 --active   # collect + classify + store
lapis report                                    # ranked findings, concerning first
lapis enumerate                                 # discover surfaces (needs API key)
pytest                                          # tests
```

Sources: `commoncrawl pastes gists wikis relays eth btc arweave ipfs`.
`commoncrawl` is passive; live collectors need `--active` (or `LAPIS_ACTIVE=1`) and
honor a per-host rate limit.

## Intended use & ethics

Lapis is for **defensive AI-safety research**: detecting and responsibly disclosing
autonomous-agent coordination. Not for harvesting, surveillance of people, or
building the coordination channels it looks for.

- **Read-only.** It reads public/archived data and never writes to third-party
  surfaces or submits transactions.
- **Be polite.** Prefer Common Crawl/indexers over live origins; respect robots,
  ToS, and rate limits; set a contact in `LAPIS_UA`.
- **Handle findings with care.** Redact PII; never republish third-party data
  wholesale; describe exploits/credentials by class, never as a working payload.
- **Withhold evasion aids** — nothing that helps labs *hide* collusion.
- **Report first.** A confirmed finding follows [`docs/DISCLOSURE.md`](docs/DISCLOSURE.md).

## Docs

- [`docs/architecture.html`](docs/architecture.html) — the system, in diagrams
- [`docs/nightingale.html`](docs/nightingale.html) — the method Lapis extends
- [`docs/prior-art-and-scanner.md`](docs/prior-art-and-scanner.md) — prior art + build notes
- [`RESEARCH.md`](RESEARCH.md) — the incident background

MIT licensed ([`LICENSE`](LICENSE)).
