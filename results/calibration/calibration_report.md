# Phase 3 Calibration Report — The Last Rescue

All numbers in this report come from files in `results/calibration/` produced by the commands listed at the end.
Only calibration instances (seed range 1,000,000+) were evaluated. No learning agent was involved, and no
validation/test instance was evaluated by any policy. The selection rules were written to `config/calibration.yaml` and
hashed **before** the first run (`rules_hash.txt`, sha256 `62ea21cb…`, 2026-11-11T19:15:32Z; first run 19:16:49Z).

## 1. Calibrated values (main configuration: L = 10, wall 0.15, hazard 0.10, V = 6, p_heavy = 0.5, n = 3)

| Quantity | Value | How it was obtained |
|---|---|---|
| H (horizon) | **105** | T90 = 73 steps (90th pct, method "higher", of steps to rescue ≥ 90% of victims, cooperative baseline, unlimited budget, cap 400); H = ceil(73 / 0.7) |
| B_ref | **64** units | 90th percentile of per-agent consumption (cooperative baseline, unlimited budget, H = 105); mean 44.9 |
| ρ levels | **Abundant 1.0, Moderate 0.5, Scarce 0.3, Critical 0.2** | pre-stated rules on the cooperative baseline's RF curve (§4) |
| Per-agent initial budget b0 | **64 / 32 / 19 / 13** | round-half-up(ρ · 64) |
| Pooled team budget | 192 / 96 / 57 / 39 | 3 · b0 |
| f4 budget thresholds | τ = (3, 16, 32) | spec §1.7 with B_ref = 64; initial buckets 3 / 3 / 2 / 1 |

Check of step 1: with H = 105 and unlimited budget, 96.0% of instances reach ≥ 90% rescues (requirement ≥ 90%).
8 of 200 instances (4%) never reach 90% even within 400 steps (cooperative-baseline limitation: e.g. two agents waiting
at different heavy victims until time-out); they are included in every statistic.

## 2. Review point 1 — budget scope, feasibility and exhaustion

Per-agent budgets of 64/32/19/13 units, no recharge, no transfer (pooled ablation: 192/96/57/39). What each level means
on the 200 calibration instances (`table_sweep_main.md`):

| Level | ρ | b0 | Solvable (oracle rescues ≥ 1) | Oracle reference RF | Cooperative RF | Greedy RF | Random RF | Cooperative episodes ending: exhausted / horizon / all rescued | Mean episode length (coop) |
|---|---|---|---|---|---|---|---|---|---|
| Abundant | 1.0 | 64 | 1.000 | 1.000 | 0.971 | 0.453 | 0.062 | 0.07 / 0.10 / 0.84 | 50.8 |
| Moderate | 0.5 | 32 | 1.000 | 0.945 | 0.696 | 0.246 | 0.028 | 0.94 / 0.00 / 0.07 | 45.2 |
| Scarce | 0.3 | 19 | 1.000 | 0.615 | 0.392 | 0.139 | 0.013 | 1.00 / 0.00 / 0.00 | 27.6 |
| Critical | 0.2 | 13 | 0.990 | 0.391 | 0.220 | 0.077 | 0.006 | 1.00 / 0.00 / 0.00 | 16.6 |

- Scarcity is budget-limited, not time-limited, at Moderate and below (≥ 94% of cooperative episodes end by
  exhaustion); at Abundant 10% end by the horizon (the 4–10% of hard instances above).
- Feasibility is exact (spec §1.4) and the oracle reference rescues ≥ 1 victim exactly when the check says it is
  possible (tested in Phase 2). At Critical 1.0% of calibration instances are infeasible; frozen experimental instance sets
  were regenerated to be feasible at Critical with rejection rates 1.4% (train), 0.0% (validation), 1.0% (test), 2.0%
  (shifted test) (`instance_sets.json`).
- The provable upper bound (action costs only) equals V at all four levels: it is valid but uninformative here, so the
  oracle reference is the meaningful "what was achievable" comparison. It is a strong heuristic (99.2% of the exhaustive
  macro-plan optimum on tiny instances, Phase 2), not a proven optimum.
- **Deviation from target (not from the rule):** Critical's cooperative RF is 0.220, above the 0.10–0.15 target band.
  The ρ value that falls nearest the band (ρ = 0.1, cooperative RF 0.043) is solvable in only 33% of instances, so the
  pre-stated feasibility constraint moved Critical up to ρ = 0.2 (99.0% solvable). The grid was not refined after seeing
  this. The four levels remain clearly separated (0.97 / 0.70 / 0.39 / 0.22; oracle 1.00 / 0.95 / 0.62 / 0.39).

## 3. Review point 3 — calibration relative to map size, density, costs and horizon

H and B_ref were recalibrated **per configuration** with the identical procedure (`table_bref.md`):

| Config | L | density | V | H | B_ref (q90) | mean consumption | analytic estimate | analytic / mean |
|---|---|---|---|---|---|---|---|---|
| main | 10 | 0.06 | 6 | 105 | 64 | 44.9 | 21.9 | 0.489 |
| L8_d04 | 8 | 0.04 | 3 | 48 | 34 | 24.2 | 11.6 | 0.479 |
| L8_d08 | 8 | 0.08 | 5 | 59 | 43 | 31.8 | 15.7 | 0.493 |
| L12_d04 | 12 | 0.04 | 6 | 150 | 87 | 59.1 | 26.8 | 0.453 |
| L12_d08 | 12 | 0.08 | 12 | 186 | 113 | 86.8 | 41.4 | 0.477 |
| main_p0 | 10 | 0.06 | 6 (all light) | 48 | 41 | 31.1 | 14.5 | 0.465 |

**Analytic cross-check.** B_ref_analytic = (1/n)[c_S·A/w² + c̄_m·(A/w + p_h·V·L/2)] + (1/n)·V[(1−p_h)c_R + p_h(c_R + c_A)],
with A the free cells, w = 2r_s + 1, c̄_m = 1 + hazard share. Across the six configurations the analytic estimate tracks
the empirical mean almost perfectly in *shape* (Pearson r = 0.998) but is consistently about **2.1× too low**
(ratio 0.45–0.49). Interpretation: the formula gets the scaling with area, density and costs right but omits a roughly
constant overhead of decentralised search: detours to known victims, overlap at sector borders, re-search, and the
second agent's travel to joint rescues being longer than L/2. This is a finding, not a failure: it is why B_ref is
defined empirically, and why per-configuration calibration is needed.

**Does ρ keep the same meaning?** (`table_sensitivity.md`, `figures/fig_cal_sensitivity.png`) Cooperative RF at the
selected levels:

| Level | main | L ≥ 10 spread (main, L12_d04, L12_d08) | L = 8 configurations | p_heavy = 0 |
|---|---|---|---|---|
| Abundant | 0.971 | 0.003 | 0.957–0.972 | 0.982 |
| Moderate | 0.696 | 0.038 | 0.485–0.603 | 0.601 |
| Scarce | 0.392 | 0.079 | 0.213–0.310 | 0.237 |
| Critical | 0.220 | 0.075 | 0.087–0.160 | 0.109 |

- For L ≥ 10, "fraction of just-enough budget" means nearly the same thing across size and density (spread ≤ 0.08 at
  every selected level), and the selection rule applied to each configuration's own curve picks the same or adjacent
  levels (main and L12_d04: identical 0.5/0.3/0.2; L12_d08: 0.5/0.3/0.1).
- On 8×8 maps the meaning drifts at low ρ (RF 0.09–0.16 at Critical vs 0.22): fixed per-rescue action costs
  (c_R = 3, c_A = 2) and the travel out of the base do not shrink with B_ref, so on small maps a given fraction of B_ref
  buys fewer rescues. L8_d04 cannot satisfy the Critical feasibility constraint at any ρ below its own Scarce. Limitation:
  conclusions about Scarce/Critical should not be extrapolated to maps smaller than 10×10.
- The alternate configuration for the robustness sweep is **L12_d04** (pre-stated default; it is solvable in 100% of
  instances at the main Critical level, so the fallback was not needed). Its own H = 150, B_ref = 87, budgets 87/44/26/17.
  Note: because its curve is close to main's, this sweep tests robustness to a larger, sparser map within the regime where
  ρ is comparable, not robustness to the small-map regime.

## 4. Review point 2 — what calibration contributes to attribution under non-stationarity

- **Cooperation is costly in resources.** With every victim light (p_heavy = 0), B_ref = 41; with half heavy, B_ref = 64
  (+56%), on identical layouts. Cooperation demand is therefore a real resource sink in this environment, which is the
  premise of the A3 difference-in-differences.
- **A3 design consequence (pre-freeze change P8).** If the p_heavy = 0 world used its own calibrated budgets (as the v0.2
  draft said), its Critical level (b0 = 8) would be solvable in only 62% (validation) / 73% (test) of the frozen main
  instances, versus ≥ 99% for p_heavy = 0.5. The DiD at Critical would then be dominated by impossible instances rather than
  by cooperation demand. The frozen design therefore makes the **primary** A3 comparison use the main configuration's H and
  B_ref in both worlds, so the two worlds differ only in victim types (the cleanest manipulation); the world-specific
  calibration (H = 48, B_ref = 41) becomes the secondary analysis, together with a DiD on oracle-normalised RF.
- **Sample-size confound (A6) is large.** Cooperative episodes last 50.8 steps at Abundant but 16.6 at Critical (3.1×).
  With equal training episodes, Critical learners would see about a third of the transitions. The pre-registered A6
  equal-environment-steps sensitivity is therefore essential, not cosmetic, and is retained unchanged.
- The four ρ levels were chosen without any learning agent, so differences between learned policies across ρ cannot have
  been engineered by the calibration.

## 5. Reproducibility

```
python scripts/run_calibration.py      # ~2 min on 2 cores -> results/calibration/{config}/*, calibration_summary.json
python scripts/plot_calibration.py     # figures + tables from the saved files
python scripts/make_instance_sets.py   # ~1 min -> results/calibration/instance_sets.json (frozen seed lists)
```
A from-scratch re-run of the main configuration reproduced H, B_ref, T90, mean consumption and every sweep value
exactly (`results/logs/calibration_rerun_check.txt`). Console logs: `results/logs/calibration_console.txt`,
`results/logs/instance_sets_console.txt`.
