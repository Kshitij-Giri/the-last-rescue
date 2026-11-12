# Phase 4 learnability pilot — protocol (written and hashed BEFORE any pilot run)

Governing rule: preregistration v1.0 §5 (H0-gate) and §9 (what the pilot may change). The SHA-256 of this file is recorded in
`results/pilot/protocol_hash.txt` before the first pilot run.

## Scope
- Condition: main configuration, **Abundant** (b0 = 64, H = 105, B_ref = 64), per-agent budgets.
- Training instances: frozen main training pool (1,000 seeds). Evaluation: frozen main **validation** list (50 seeds) only.
  Test and shifted-test instances are not loaded.
- Pilot seeds: **1000–1004** (5 seeds), disjoint from the confirmatory seeds 0–9, so the Phase 5 results are fresh replicates.
- Baselines evaluated on the same 50 validation instances at Abundant for reference: random (10 evaluation seeds, 0–9),
  greedy, cooperative, oracle reference (full information; reported separately, never as a learner).

## Variant order (permitted parameters only; costs, rewards, λ, ρ levels, metrics, tests and instances are fixed)
- **P0 (frozen defaults):** α = 0.1, γ = 0.98, ε 1.0 → 0.05 over the first 70% of episodes, 8,000 episodes, observation as in
  spec §1.7.
- If P0 fails the gate, try in this order and stop at the first variant that passes:
  P1 α = 0.2; P2 α = 0.05; P3 ε decay over 90% of episodes (α = 0.1); P4 16,000 episodes (α = 0.1, decay 70%);
  P5 an observation-bucket change designed from the failure diagnosis, written into this file's appendix before it is run.
- If P0 passes, no other α / ε variant is tried (no tuning beyond what is needed to pass the gate).

## Gate (validation analogue of the preregistered H0-gate)
IQL final-checkpoint validation RF > random baseline validation RF, with one-sided Wilcoxon signed-rank p < 0.05 over the 5
seeds (with n = 5 this requires all 5 seeds above random: p = 1/32 = 0.031) and δ_1 = (#above − #below)/5 ≥ 0.33.
The confirmatory H0-gate on the test set with seeds 0–9 is run in Phase 5, as preregistered.

## Episode-count rule (applies to the variant that passes the gate)
Keep its episode count unless the 5-seed mean validation RF rises by more than 0.02 between the checkpoints at 75% and 100% of
training (still learning). In that case run the same variant with twice the episodes (5 pilot seeds) and adopt the longer
schedule if its final mean validation RF exceeds the shorter one's by more than 0.02 and the Phase 5 compute estimate stays
within about 2 h on a 4-core laptop (otherwise keep the shorter one and report the limitation).

## Descriptive questions (no decision depends on them)
- Do independent learners learn the same-step RESCUE + ASSIST? Reported per seed: share of heavy victims rescued, ASSIST
  actions, effective-assist rate, cooperation rate, abandonment events (E1), on validation at the final checkpoint.
  Pre-stated reading: "learned joint rescue" if the heavy-victim rescue share is ≥ 0.10 in at least 3 of 5 seeds;
  "not learned" if it is < 0.02 in at least 3 of 5 seeds; otherwise "partially/unreliably learned".
- Learning curves, policy churn, mean |TD error| and the preregistered stability criterion per seed.
- Measured run time, to update the Phase 5 compute estimate.

## Appendix (P5 design, filled only if needed before running P5)
(empty)
