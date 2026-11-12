# Phase 4 Learnability Pilot — Report

Protocol: `docs/pilot_protocol.md`, hashed before the first pilot run (`results/pilot/protocol_hash.txt`,
sha256 `51a4bdc5…`, 2026-11-11T19:35:13Z) and unchanged afterwards (re-hashed after the run: identical).
Setting: main configuration, **Abundant** (b0 = 64, H = 105, B_ref = 64), per-agent budgets; 5 pilot seeds (1000–1004,
disjoint from confirmatory seeds 0–9); training on the frozen 1,000-instance training pool; evaluation on the frozen 50
**validation** instances only. Test and shifted-test instances were never loaded. **These are pilot (validation) numbers, not
experimental results.**

## 1. Decision trail (all pre-stated)

| Step | Rule | Outcome |
|---|---|---|
| Variant | P0 = frozen defaults (α 0.1, γ 0.98, ε 1.0→0.05 over 70%, 8,000 episodes, spec observation) | run |
| Gate | IQL validation RF > random, one-sided Wilcoxon p < 0.05 (n = 5 ⇒ all 5 above) and δ₁ ≥ 0.33 | **PASSED**: 5/5 seeds above random, p = 0.031, δ₁ = 1.0 |
| Other variants | only if P0 fails | **not run** (P1–P5 unused) |
| Episode count | double only if mean validation RF rises > 0.02 from 75% to 100% of training | rise = **0.018** → keep **8,000** (borderline; see §5) |

**Net result: no permitted parameter was changed.** Phase 5 uses α = 0.1, γ = 0.98, ε 1.0 → 0.05 over the first 70% of
8,000 episodes, and the observation of spec §1.7, exactly as frozen.

## 2. Seed-level results at the final checkpoint (validation, greedy policy, 50 instances each)

| Seed | RF | Heavy share | Light share | ASSISTs / ep | EAR | CR | E1 abandon / ep | TDI | Steps | Ended by horizon | Churn (last) | RF range (last 3) | Stable |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1000 | 0.717 | 0.613 | 0.820 | 3.74 | 0.492 | 0.264 | 3.20 | 0.305 | 98.3 | 0.88 | 0.092 | 0.210 | no |
| 1001 | 0.663 | 0.527 | 0.800 | 3.58 | 0.441 | 0.224 | 2.60 | 0.414 | 99.4 | 0.90 | 0.117 | 0.050 | no |
| 1002 | 0.503 | 0.327 | 0.680 | 6.48 | 0.151 | 0.143 | 5.64 | 0.674 | 105.0 | 1.00 | 0.181 | 0.073 | no |
| 1003 | 0.700 | 0.580 | 0.820 | 3.22 | 0.540 | 0.248 | 3.12 | 0.462 | 93.4 | 0.76 | 0.085 | 0.213 | no |
| 1004 | 0.527 | 0.320 | 0.733 | 2.94 | 0.327 | 0.126 | 6.58 | 0.659 | 103.4 | 0.96 | 0.116 | 0.157 | no |
| **mean** | **0.622** | 0.474 | 0.771 | | | | | | | | | | **0/5** |

Reference on the same 50 validation instances (`baselines_validation_abundant.json`):

| Policy | RF | Heavy share | EAR | CR | Mean steps |
|---|---|---|---|---|---|
| Random (10 eval seeds) | 0.066 | 0.001 | 0.062 | 0.000 | 63.7 |
| Greedy | 0.470 | 0.000 | undefined (never ASSISTs) | 0.000 | 50.4 |
| Cooperative (hand-designed) | 0.983 | 0.967 | 0.895 | 0.457 | 45.9 |
| Oracle reference (full information, centralized; not a learner) | 1.000 | 1.000 | 1.000 | 0.792 | 28.2 |

## 3. Can independent learners learn the same-step RESCUE + ASSIST?

**Yes, partially.** Pre-stated reading: "learned joint rescue" (heavy-victim share ≥ 0.10 in ≥ 3 of 5 seeds): all 5 seeds
rescue 32–61% of heavy victims (random 0.1%, greedy 0%). But the joint behaviour is much less reliable than in the
hand-designed policy:
- effective-assist rate 0.15–0.54 (cooperative baseline 0.90): roughly half or more of the ASSISTs are wasted;
- 2.6–6.6 abandonment events (E1) per episode: one agent RESCUEs or ASSISTs while a co-located teammate does something else;
- heavy victims are rescued less often than light ones in every seed (0.32–0.61 vs 0.68–0.82).
- Learned teams WAIT 54–63% of the time, SEARCH in only 1–3% of actions, and spend about 80% of the team budget
  (`P0/behaviour_diagnostic.txt`); most episodes end at the horizon (76–100%), i.e. at Abundant the learned teams are
  time-limited, unlike the cooperative baseline (84% of its episodes end with all victims rescued).

## 4. Learning dynamics and non-stationarity (`figures/fig_pilot_P0.png`)

- Validation RF stays at the untrained level (≈ 0.07, random-like tie-breaking) until about episode 2,000, rises steadily,
  and first exceeds the greedy baseline (0.47) between episodes 5,500 and 6,000 in every seed — i.e. shortly after ε reaches
  its floor (episode 5,600). The heavy-victim share follows the same pattern: joint rescues become frequent only once
  exploration noise is low, plausibly because a random action by either partner breaks a same-step RESCUE + ASSIST.
- Seed-to-seed spread at the end is large (RF 0.50–0.72), so seed-level reporting (10 seeds in Phase 5) is necessary.
- **Stability: 0 of 5 runs meet the preregistered criterion** (churn < 5% and RF range < 0.02 over the last three
  checkpoints). Final churn is 8.5–18%; validation RF moves by 0.05–0.21 across the last three checkpoints; mean |TD error|
  is still increasing at 8,000 episodes. With a constant α, a 5% ε floor and co-learning teammates this is not surprising:
  the policies have not converged and keep shifting as teammates shift. This is direct evidence of the non-stationarity the
  review raised.

## 5. Failures, limitations and open points

1. **Stability criterion is not met by any pilot run.** If this holds in Phase 5, the preregistered sensitivity "repeat the
   main result on stable runs only" will have no runs. The preregistration (§6) says unstable runs are not excluded; the
   plan stays as frozen and this will be reported as a result. The best-on-validation checkpoint (preregistered sensitivity)
   becomes more informative because final-checkpoint RF fluctuates by up to ±0.1.
2. **Episode count is borderline.** The last-quarter rise (0.018) is just below the 0.02 trigger, and TD error is still
   rising, so longer training might raise performance. The pre-stated rule says keep 8,000; changing it now would be a
   data-dependent deviation, so it is not done. Learned performance in Phase 5 should be read as "after 8,000 episodes",
   not as converged.
3. **Time-limited at Abundant.** Learned teams mostly end at the horizon with ~20% of the team budget unspent, whereas H was
   calibrated on the cooperative baseline. At Abundant the learned teams are therefore partly time-limited; termination
   shares per ρ (preregistered) will show whether scarcity turns this into budget limitation at lower ρ.
4. **Pilot evaluated only Abundant.** Whether learning works at lower ρ is unknown until Phase 5 (deliberately not piloted,
   so that no setting was tuned on the scarcity conditions).
5. The pilot gate used validation instances and 5 pilot seeds; the confirmatory H0-gate (test set, seeds 0–9) is part of
   Phase 5.

## 6. Compute (measured)

One 8,000-episode run at Abundant: 96.6–101.1 s, ≈ 711,000 environment steps (≈ 140 µs per step including 17 validation
checkpoints) on one core here; building the training and validation pools takes about 22 s once per worker process.
Phase 5 estimate (≈ 230 training runs; scarcer levels have shorter episodes, so ≤ 100 s per main-configuration run, the
alternate 12×12 configuration slower): about 4.5–6.5 CPU-hours → about 1.2–1.7 h on a 4-core laptop and 2.5–3.5 h on this
2-core environment. Phase 5 will therefore run in resumable chunks.

## 7. Commands

```
python scripts/run_pilot.py --baselines          # baselines on validation, Abundant
python scripts/run_pilot.py --variant P0         # 5 pilot seeds, 5 min 17 s on 2 cores
python scripts/analyze_pilot.py P0               # gate, episode rule, joint-rescue reading, figure
```
Raw logs per seed: `results/pilot/P0/seed_*/{train_log.csv, checkpoints.csv, val_final_episodes.csv, q_final.npz,
q_bestval.npz, run.json}`; console logs in `results/logs/pilot_*`.
