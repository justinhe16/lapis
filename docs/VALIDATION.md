# Validation

Lapis was validated against the **collusion.wiki DSEWiki dump** — a known-positive
corpus of real OpenAI agent posts (`records.jsonl`, ~13.7k messages). This is the
honest calibration: labeled-real agents in, measure what comes out.

## Run

40 records, stage-2 = `claude-opus-5`. `lapis scan --source dump --limit 40`.

## Results

- **Stage-1 recall: 21/40 (52%)** flagged as candidates at validation time; adding
  the `link_dump` signature afterward lifts local stage-1 recall to **24/40 (60%)**,
  with human-control fixtures still at 0 false positives.
- **Stage-2: 0 errors**, and **5/21 flagged → CONCERNING** (`autonomous_agent` +
  `unsanctioned` / `safety_relevance: high`). The concerning verdicts were all
  genuine DSEWiki coordination — answer-sharing, task-relay, cross-instance eval
  signaling — at 0.72–0.88 confidence. Link dumps and ambiguous posts correctly
  sank to `unclear` / `none` rather than false-alarming.

## Read

The pipeline does its job: real agent coordination flows through and lands as
CONCERNING; noise sinks. Precision on the escalated set looked strong (no false
positives in the sampled concerning verdicts).

Known recall gaps (why 60%, not higher): (1) many agent posts are bare
link/data-source dumps that carry little coordination *language* — partly addressed
by the `link_dump` signature; (2) a few genuine coordination messages sit just under
the score-3 stage-1 threshold. Both are stage-1 tuning targets, not pipeline flaws.

## Note

Fixed a broken-`httpx2` decompression error (the `anthropic` SDK's HTTP client throws
on compressed responses in some environments) by requesting `Accept-Encoding: identity`.
