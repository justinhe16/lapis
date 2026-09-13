#!/usr/bin/env bash
# Lapis continuous loop: fire bounded scan batches across sources on an interval.
# Everything stays bounded per batch (--limit) and polite (per-host rate limit);
# dedup means re-runs don't double-count. Ctrl-C stops cleanly.
#
# Config (env):
#   LOOP_SOURCES         space-separated sources      (default: "gists commoncrawl pastes wikis relays")
#   LOOP_LIMIT           --limit per batch            (default: 50)
#   LOOP_SLEEP           seconds between batches        (default: 60)
#   LOOP_ITERS           total batches; 0 = infinite    (default: 0)
#   LOOP_REPORT_EVERY    print a report every N rounds  (default: 1)
#   LOOP_ENUMERATE_EVERY re-run `enumerate` (agent discovers new targets) every N
#                        rounds, 0 = never; runs once at start if >0 (default: 0,
#                        needs ANTHROPIC_API_KEY). Discovered targets feed the
#                        commoncrawl/wikis/relays collectors automatically.
#
# Examples:
#   scripts/loop.sh                                  # infinite, gists + commoncrawl
#   LOOP_SOURCES="gists pastes" LOOP_SLEEP=120 scripts/loop.sh
#   LOOP_ITERS=6 LOOP_LIMIT=40 scripts/loop.sh       # stop after 6 batches
set -u

SOURCES="${LOOP_SOURCES:-gists commoncrawl pastes wikis relays}"
LIMIT="${LOOP_LIMIT:-50}"
SLEEP_S="${LOOP_SLEEP:-60}"
ITERS="${LOOP_ITERS:-0}"
REPORT_EVERY="${LOOP_REPORT_EVERY:-1}"
ENUMERATE_EVERY="${LOOP_ENUMERATE_EVERY:-0}"

export LAPIS_ACTIVE=1          # allow read-only live polling (commoncrawl is passive regardless)

trap 'echo "[loop] stopping (signal)"; exit 0' INT TERM

run_enumerate() {
  echo "[loop] $(date -u +%H:%M:%S) enumerate — discovering new targets"
  lapis enumerate >/dev/null 2>&1 && echo "[loop] enumerate ok (targets fed to collectors)" \
    || echo "[loop] enumerate skipped/failed (needs ANTHROPIC_API_KEY) — continuing"
}

batches=0
round=0
echo "[loop] sources: $SOURCES | limit: $LIMIT | sleep: ${SLEEP_S}s | iters: ${ITERS:-inf} | enumerate every: ${ENUMERATE_EVERY}"
[ "$ENUMERATE_EVERY" -gt 0 ] && run_enumerate
while :; do
  for src in $SOURCES; do
    echo "[loop] $(date -u +%H:%M:%S) scan $src --limit $LIMIT"
    lapis scan --source "$src" --limit "$LIMIT" || echo "[loop] scan $src failed — continuing"
    batches=$((batches + 1))
    if [ "$ITERS" -ne 0 ] && [ "$batches" -ge "$ITERS" ]; then
      echo "[loop] reached $batches batches — final report:"
      lapis report | head -n 8
      exit 0
    fi
    sleep "$SLEEP_S"
  done
  round=$((round + 1))
  if [ "$REPORT_EVERY" -gt 0 ] && [ $((round % REPORT_EVERY)) -eq 0 ]; then
    echo "[loop] --- report after round $round ---"
    lapis report | head -n 8
  fi
  if [ "$ENUMERATE_EVERY" -gt 0 ] && [ $((round % ENUMERATE_EVERY)) -eq 0 ]; then
    run_enumerate
  fi
done
