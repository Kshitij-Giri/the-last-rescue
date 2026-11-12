# Module owners

Roles follow the project proposal. The **owner** is the member who presents and defends the module in the viva. Every member must still be able to explain every module at the level of `docs/viva_guide.md`.

| Member | Proposal role | Owns (code) | Owns (documents / results) |
|---|---|---|---|
| **Kshitij Suresh Giri** (23110177) | Coordination, formal problem, integration, report integration | `src/tlr/calibration.py`, `src/tlr/stats.py`, `src/tlr/utils.py`; scripts `run_calibration.py`, `plot_calibration.py`, `make_instance_sets.py`, `make_freeze_manifest.py`, `run_stats.py`, `verify_results.py`, `make_manifest.py`, `build_report_content.py`, `report_lib.py`, `render_report.js`, `build_report.sh`, `run_all.py` | `docs/phase0_design_spec.md` §1, §4, §5; `docs/preregistration.md`; `docs/deviations_log.md`; `docs/claims.yaml`; report Sections 1, 3, 5, 8, 10, 12–14; Review Response Matrix |
| **Panjari Maheshkumar Patel** (23110236) | Environment, grid-world, maps, resources, interfaces, logging | `src/tlr/env.py`, `src/tlr/mapgen.py`, `src/tlr/costs.py`, `src/tlr/observation.py`, `src/tlr/replay.py`; scripts `bench_env.py`, `make_sample_replays.py`, `make_report_diagrams.py` | Tests: env rules, masking, feasibility, pooled budget, stale information, observation, mapgen, invariants. Report Section 4, Fig. 0a/0b. Replays `results/replays/phase1_*` |
| **DV Snehal** (23110083) | Multi-agent formulation, reward and cooperation modelling, baselines, individual vs collective analysis | `src/tlr/rewards.py`, `src/tlr/cooperation_metrics.py`, `src/tlr/metrics.py`, `src/tlr/baselines.py`, `src/tlr/oracle.py`, `src/tlr/evaluate.py`; scripts `validate_metrics.py`, `make_phase2_replays.py`, `make_replays.py` | Tests: metrics, baselines, oracle. `results/phase2/` (metric validity). Report Sections 6.2–6.3, 7, 9.4–9.5, 10.8 (A8), Exp4 |
| **Kshitish Madbhavi** (24110175) | RL implementation, Q-learning pipeline, learning curves, evaluation, ablations | `src/tlr/iql.py`, `src/tlr/train.py`, `src/tlr/experiments.py`; scripts `run_pilot.py`, `analyze_pilot.py`, `run_experiments.py`, `run_phase5_chunk.sh`, `check_phase5_integrity.py`, `phase5_summary.py`, `make_tables.py`, `make_figures.py` | Tests: IQL, experiments, quick run. `results/pilot/`, `results/runs/`, `results/eval/`, `results/phase5/`, figures 1–9. Report Sections 6.1, 9.1–9.3, 10.2–10.7, 11 |

## What each owner must be able to do live

- **Kshitij:**
  - explain the calibration rules and why Critical is 0.2;
  - explain the unit of analysis, Friedman, Page, Wilcoxon, Holm and the bootstrap;
  - explain why H5 makes no claim;
  - run `verify_results.py` and explain V1–V7.
- **Panjari:**
  - walk through one step of `env.step` in the order of Fig. 0b;
  - show a masked action raising `InvalidActionError`;
  - explain exhaustion, dormancy and feasibility;
  - show a replay.
- **Snehal:**
  - compute CR, EAR and TDI by hand on a scripted episode from `tests/test_metrics.py`;
  - explain why PSS tracks reward;
  - explain the baselines (greedy lockstep, cooperative conventions) and why the oracle is a reference, not a learner.
- **Kshitish:**
  - explain the IQL update, the ε schedule, masking in argmax, and the no-update rule for dormant agents;
  - explain non-stationarity, churn and TD error;
  - run `run_all.py --quick`;
  - explain A1 (mismatch construction), A2, A4 (and its confound) and A6.
