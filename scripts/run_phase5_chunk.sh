#!/usr/bin/env bash
# Run a list of orchestrator commands, appending all output to results/logs/phase5_console.txt (resumable; see
# scripts/run_experiments.py). Usage: bash scripts/run_phase5_chunk.sh "train --block main" "eval --kind A1" ...
cd "$(dirname "$0")/.."
LOG=results/logs/phase5_console.txt
for c in "$@"; do
  echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) START python3 scripts/run_experiments.py $c" >> "$LOG"
  start=$(date +%s)
  python3 scripts/run_experiments.py $c >> "$LOG" 2>&1
  rc=$?   # captured immediately (the Phase 5 run logged the status of an echo sub-expression instead; see deviations C2)
  echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) END ($(( $(date +%s) - start )) s, exit $rc) $c" >> "$LOG"
done
