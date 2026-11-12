# The Last Rescue — Learning to Cooperate Under Resource Scarcity

Foundations of AI, Group 14, IIT Gandhinagar: Kshitij Suresh Giri (23110177), Panjari Maheshkumar Patel (23110236),
DV Snehal (23110083), Kshitish Madbhavi (24110175).


A preregistered multi-agent RL study. Three independent tabular Q-learners rescue victims on a 10 x 10 grid with private,
non-refillable budgets; heavy victims need RESCUE + ASSIST by two agents in the same step. Scarcity rho is a fraction of a
calibrated just-enough budget (B_ref = 64, H = 105; rho = 1.0 / 0.5 / 0.3 / 0.2 -> budgets 64 / 32 / 19 / 13).
350 training runs x 8,000 episodes, 10 seeds per condition, 100 frozen test maps. Results are "after 8,000 episodes"
(no run converged); the oracle is a full-information reference, not a learner.

## Setup
```bash
python3.13 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt      # numpy, scipy, pandas, matplotlib, PyYAML, pytest (pinned)
# report rendering only: Node.js with the `docx` npm package, LibreOffice (PDF), poppler-utils (pdfinfo/pdftotext)
```

## Quick start
```bash
python -m pytest -q                  # all tests
python scripts/run_all.py --quick    # whole pipeline at reduced scale (3 seeds x 3,000 episodes), < 10 min on 2 cores
                                     # -> results_quick/ (never touches results/; numbers are a pipeline check only)
python scripts/verify_results.py     # recompute confirmatory statistics, check every claim and every report number
python scripts/run_all.py --full     # the full study (about 2.5 h on 2 cores, then stats, figures, report)
```

## All commands (in pipeline order)
```bash
python -m pytest -q                         # full test suite (264 tests, about 25 s)
python scripts/bench_env.py                 # environment speed -> results/logs/bench_env.txt
python scripts/make_sample_replays.py       # ASCII replays -> results/replays/phase1_*.txt
python scripts/validate_metrics.py          # metric construct-validity check (~10 s) -> results/phase2/
python scripts/make_phase2_replays.py       # baseline/oracle replays -> results/replays/phase2_*.txt
python scripts/run_calibration.py           # calibration, ~2 min on 2 cores -> results/calibration/
python scripts/plot_calibration.py          # calibration figures + tables (from saved files)
python scripts/make_instance_sets.py        # frozen instance seed lists, ~1 min -> results/calibration/instance_sets.json
python scripts/make_freeze_manifest.py      # SHA-256 of every frozen file -> results/calibration/freeze_manifest.json
python scripts/make_freeze_manifest.py --check   # list frozen files changed since the freeze
python scripts/run_pilot.py --baselines     # pilot baselines on validation (Abundant)
python scripts/run_pilot.py --variant P0    # learnability pilot, 5 seeds, ~5 min on 2 cores -> results/pilot/P0/
python scripts/analyze_pilot.py P0          # gate + figures -> results/pilot/
python scripts/run_experiments.py status    # Phase 5: what is done / remaining (resumable)
bash scripts/run_phase5_chunk.sh "train --block main" "eval --kind learned" ...   # run stages, log to results/logs
python scripts/check_phase5_integrity.py    # every run/eval part present and well-formed
python scripts/phase5_summary.py            # seed-level tables + H0-gate -> results/phase5/
python scripts/make_phase5_manifest.py      # SHA-256 of all Phase 5 artefacts
python scripts/run_stats.py                 # Phase 6: full statistical battery from raw episodes (~25 s) -> results/stats/
python scripts/make_tables.py               # tables -> results/tables/, summary -> results/stats/stats_summary.md
python scripts/make_figures.py              # figures -> results/figures/ (~2 min)
python scripts/make_replays.py              # replay evidence from test episodes -> results/replays/phase6_*
python scripts/verify_results.py            # independent verification + claims ledger; exits 1 on any mismatch
bash scripts/build_report.sh                # Phase 7: report/report.docx + report.pdf from result files (~10 s)
python scripts/make_manifest.py             # results/manifest.json (SHA-256 of every file)
```

## Layout
- `config/` — `default.yaml` (every constant), `calibration.yaml` (pre-stated rules), `calibrated.yaml` (calibrated values).
- `src/tlr/` — environment (`env.py`, `mapgen.py`, `costs.py`, `observation.py`, `rewards.py`, `replay.py`), baselines and
  oracle (`baselines.py`, `oracle.py`, `evaluate.py`), metrics (`cooperation_metrics.py`, `metrics.py`), calibration,
  learning (`iql.py`, `train.py`, `experiments.py`), statistics (`stats.py`), helpers (`utils.py`).
- `scripts/` — one script per pipeline stage (above), `run_all.py` (--quick / --full), report build, verifier, manifests.
- `tests/` — 264 tests (rules, masking, budgets, stale information, feasibility, invariants, baselines, oracle, metrics on
  scripted episodes, IQL, experiments, statistics, quick run).
- `results/` — `calibration/` (frozen instance sets, freeze manifest), `pilot/`, `runs/` (350 training runs: Q-tables,
  checkpoints, logs), `eval/` (raw test episodes), `phase5/`, `stats/`, `tables/`, `figures/`, `replays/`, `logs/`,
  `manifest.json` (SHA-256 of every file).
- `report/` — `report.pdf`, `report.docx`, `report_source.md` (same content as Markdown), `content.json`, `toc_pages.json`.
- `docs/` — design spec, preregistration (FROZEN v1.0), decision log D1–D28, deviations log, claims ledger,
  `report_numbers.yaml`, references verification, phase summaries, viva guide, module owners, final audit.
- `results_quick/` — output of the last `--quick` run (pipeline check, not study results).
