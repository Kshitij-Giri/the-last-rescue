# Pre-registration — The Last Rescue

Status: **FROZEN v1.0 — 2026-11-12, end of Phase 3, before any learning run.** Calibrated values are filled in from
`results/calibration/` (report: `results/calibration/calibration_report.md`). The SHA-256 of this file, of the design spec and
of every calibration output is recorded in `results/calibration/freeze_manifest.json` (and later copied into
`results/manifest.json`). Every later change goes to `docs/deviations_log.md` ("Deviations after freeze") with date and reason.
The learnability pilot (Phase 4) uses validation instances only and may change only items listed in Section 9, each logged as
a deviation.

## 1. Research question
How does resource scarcity (ρ) affect the ability of independently learning agents to learn cooperative rescue strategies, and is any
effect of ρ on rescue performance attributable to cooperation?
Consistent with the proposal, no direction is assumed: all confirmatory tests are two-sided unless stated otherwise.

## 2. Conditions
- Main: per-agent budgets B_0^i = round(ρ·B_ref), **B_ref = 64, H = 105**, ρ ∈ {Abundant = 1.0, Moderate = 0.5, Scarce = 0.3,
  Critical = 0.2} → **b0 = 64 / 32 / 19 / 13**; p_heavy = 0.5, L = 10, n = 3, V = 6, wall 0.15, hazard 0.10.
- A3: p_heavy = 0 on the same instance seeds (same layouts and victim cells, all victims light). **Primary: the main H = 105
  and B_ref = 64** (identical absolute budgets; the worlds differ only in victim types). Secondary: the p_heavy = 0 world's
  own calibration (H = 48, B_ref = 41 → b0 = 41 / 21 / 12 / 8). (Pre-freeze change P8; reason in the calibration report §4.)
- A4: solo-trained agents deployed as a team.
- A6: equal-environment-steps training.
- Ablation: pooled team budget B_team = 3·b0 = 192 / 96 / 57 / 39 (main H and B_ref).
- Alternate configuration: one sweep on **L = 12, density 0.04** (pre-stated default retained), own calibration H = 150,
  B_ref = 87 → b0 = 87 / 44 / 26 / 17, same ρ values, its own frozen instance sets.
- Shifted test set (Exp5): wall 0.25, victim density 0.09, main H and B_ref.
- Baselines: random, greedy, hand-designed cooperative, oracle reference — evaluated on the same instances.

## 3. Units, seeds, instances
- Unit of analysis for learned policies: the **training seed** s ∈ {0,…,9}. A seed is one independent replicate of the whole
  training process. Each seed contributes exactly one number per condition and outcome: the mean over the 100 fixed test
  instances (test episodes are repeated measurements of one trained team, not independent replicates; they are never used as n).
- Ratio metrics (C1 EAR, C2 RSR, RSR_other, C4a PSS, C5 CR) are pooled per seed over the 100 test episodes
  (sum of numerators ÷ sum of denominators), so a seed's value is undefined only if the denominator is 0 in all 100 episodes.
- Training seeds 0–9 (10 per condition). Same seed ⇒ same training-map order and exploration RNG stream in every condition
  (all ρ levels, both p_heavy worlds, joint vs solo training, equal-episodes vs equal-steps, per-agent vs pooled budgets).
  Together with the shared test instances, this makes seed s a **block**: conditions compared within the same configuration are
  matched by s. All such comparisons use paired (within-seed) tests.
- Baselines: greedy, cooperative and oracle are deterministic given the instance, so each has one fixed value per ρ (mean over
  the 100 test instances); the random baseline is evaluated with 10 evaluation seeds and its value is the mean over all 1,000
  episodes. Comparisons of IQL against a baseline are therefore **one-sample** comparisons of the 10 seed values against a
  constant (neither paired nor two-sample).
- Independent comparisons: only where no seed matching exists, i.e. comparisons across different map configurations
  (main vs alternate configuration). These are not part of any confirmatory test.
- Test instances: 100 (seed range 4,000,000+), identical for all methods and conditions; shifted test: 100 (5,000,000+);
  validation: 50 (3,000,000+), used for checkpoints and the pilot only; training pool: 1,000 (2,000,000+). Every list is frozen in
  `results/calibration/instance_sets.json` (seeds + SHA-256 of the instances). Instances infeasible at Critical (b0 = 13) were
  regenerated with the next attempt seed: rejection 1.4% train, 0.0% validation, 1.0% test, 2.0% shifted test; alternate
  configuration 0.2% / 0.0% / 0.0%. A3 reuses the main lists unchanged (feasible at the primary budgets by construction).
- Evaluation is greedy (ε = 0); ties broken by RNG seeded with (instance id, agent id).
- Primary policy = final checkpoint. Sensitivity = best-validation checkpoint.

## 4. Outcomes
Primary: rescue fraction RF = rescued / V.
Secondary performance: mission success, oracle-normalized RF, collective return, individual returns, resource efficiency (rescued per
100 units), coverage, termination-reason shares.
Cooperation (definitions in `phase0_design_spec.md` §3, frozen with this file): C1 EAR, C2 RSR and RSR_other, C3 TDI,
C4a PSS, C4b consumption Gini (and remaining-budget Gini), C5 CR.
Exp4 events: E1 abandonment, E2 duplicate light rescue, E3 per-episode individual/collective conflict.

## 5. Hypotheses and tests

### 5.1 Which comparisons are paired, one-sample, or independent
| Comparison | Design | Test | Effect size |
|---|---|---|---|
| 4 ρ levels together (H1, H2) | paired, 10 complete blocks (seeds) × 4 levels | Friedman; trend: Page's L | Kendall's W |
| Two ρ levels (pairwise) | paired by seed | Wilcoxon signed-rank | matched-pairs rank-biserial r; median paired difference |
| IQL vs a baseline (H0-gate, H3) | one-sample (10 seed values vs a constant) | one-sample Wilcoxon signed-rank | δ_1 = (#seeds above − #seeds below)/10; median difference |
| Original vs mismatched teams (H4) | paired by seed (mismatch score of seed s, spec §5 A1) | Wilcoxon signed-rank | rank-biserial r |
| DiD across p_heavy worlds (H5) | paired by seed (DiD_s, spec §5 A3) | Wilcoxon signed-rank on DiD_s vs 0 + paired bootstrap CI | mean DiD |
| Joint vs solo-trained teams (H6) | paired by seed | Wilcoxon signed-rank | rank-biserial r |
| Exploratory: pooled vs per-agent, equal-steps vs equal-episodes, transfer matrix (same seed s) | paired by seed | Wilcoxon signed-rank | rank-biserial r |
| Exploratory: main vs alternate configuration | independent (different instances) | descriptive only (CIs side by side) | — |

Test details (fixed now):
- Wilcoxon: two-sided unless stated; zero differences are dropped (`zero_method="wilcox"`) and their number is reported; exact
  null distribution when there are no ties or zeros, otherwise normal approximation with continuity correction.
  With n = 10 the smallest attainable two-sided p is 2/1024 ≈ 0.002, which is below the strictest Holm threshold used here
  (0.05/12 ≈ 0.004), so every family can in principle reach significance.
- Page's L is one-directional; we test both orderings (RF increasing with ρ, RF decreasing with ρ) and report the two-sided
  p = min(1, 2·min(p_inc, p_dec)). The ρ ordering is Abundant > Moderate > Scarce > Critical.
- Missing values in paired tests: if a seed's metric is undefined in any level of a comparison (only possible for C1/C2 when a team
  never ASSISTs/SEARCHes in 100 episodes), that seed is dropped from that comparison only (complete-block analysis); the number
  of seeds used is reported with every test.

### 5.2 Hypotheses
H0-gate (learnability, one-sided): at Abundant, IQL RF > random RF. One-sample Wilcoxon (alternative "greater") of the 10 seed
  values against the random baseline's value. Required: p < 0.05 and δ_1 ≥ 0.33.
  If the gate fails: the environment/observation is simplified, re-piloted on validation data, and the change is logged; the
  main sweep does not start until the gate passes.
H1 RF differs across ρ: Friedman (blocks = seeds); trend: Page's L (two-sided as above). Follow-up: all 6 pairwise Wilcoxon
  signed-rank tests, Holm across the 6.
H2 Each cooperation metric (C1 EAR, C2 RSR, RSR_other, C3 TDI, C4a PSS, C4b consumption Gini, C5 CR) differs across ρ:
  Friedman per metric, Holm across the 7; pairwise Wilcoxon follow-ups, Holm across the 6 pairs within each metric.
H3 IQL vs each baseline at each ρ: one-sample Wilcoxon (two-sided), Holm across 4 ρ × 3 baselines (12 tests). The oracle is reported
  as a reference (oracle-normalized RF), not tested.
H4 (A1) Mismatched teams differ from original teams: Wilcoxon signed-rank paired by seed, per ρ; Holm across the 4 ρ.
  Caveat stated in the report: each agent appears in several mismatched teams, so the 10 paired differences are not perfectly
  independent; the test is therefore read together with the per-seed plot.
H5 (A3) DiD ≠ 0: Wilcoxon signed-rank on the 10 values DiD_s; estimate = mean DiD_s with 95% paired bootstrap CI (resampling
  seeds, so each resampled seed keeps all four of its values together). Primary: both worlds at the main H and B_ref.
  Secondary (reported, not tested): (a) p_heavy = 0 world at its own calibration; (b) DiD on oracle-normalised RF.
H6 (A4) Jointly trained teams differ from solo-trained teams: Wilcoxon signed-rank paired by seed, per ρ; Holm across the 4 ρ.
Exploratory (labelled as such in the report): A2 ablation, A5 diagnostics, A8 mediation regression, Exp5 transfer matrix and
  shifted test, pooled-budget ablation, alternate configuration, equal-steps sensitivity.

Interpretation constraints fixed before any result (group decisions, D22): C4a PSS stays in the H2 family but is reported
next to its correlation with collective return (Phase 2: Spearman 1.000 / 0.984 / 0.951) and is never presented as independent
evidence of cooperation. Comparisons with the greedy baseline are read as "uncoordinated identical agents" (its agents move in
lockstep), not as the best selfish policy.

### 5.3 Secondary (robustness only, unpaired)
For comparability with the original plan, Kruskal–Wallis (H1, H2) and Cliff's δ for pairwise ρ comparisons are also reported,
labelled as secondary. They ignore the pairing, so they are less powerful; conclusions are drawn from the paired tests.

### 5.4 Reporting
Condition values: mean ± 95% percentile bootstrap CI (10,000 resamples of seeds). Paired contrasts: mean of the within-seed
differences ± 95% paired bootstrap CI (resample seeds, keep each seed's conditions together). n seeds stated, per-seed points
connected across conditions (so the pairing is visible) on every plot.
Significance level α = 0.05 after Holm correction within each family above. All bootstrap and permutation RNGs use fixed seeds.

## 6. Convergence/stability criterion (A5)
A run is "stable" iff policy churn < 5% between its last two checkpoints and validation RF varies by < 0.02 across its last three
checkpoints. Unstable runs are NOT excluded; the share of stable runs per condition is reported and the main result is repeated on
stable runs only as a sensitivity.

## 7. Exclusions
No training run is excluded for its outcome. A run is excluded only for a crash or a detected implementation bug, which is
documented; after a bug fix all affected conditions are re-run.

## 8. Calibration (Phase 3, completed)
Procedure as pre-stated in `config/calibration.yaml` (hashed before the first run). Results on 200 calibration instances:
H = 105 (T90 = 73), B_ref = 64. Cooperative-baseline RF at the selected levels 0.971 / 0.696 / 0.392 / 0.220; oracle reference
1.000 / 0.945 / 0.615 / 0.391; solvable share 1.000 / 1.000 / 1.000 / 0.990. Critical lies above the 0.10–0.15 target band
because the band-matching ρ = 0.1 is solvable in only 33% of instances (pre-stated feasibility rule). Calibration never used
the RL agents or any validation/test instance.

## 9. What the Phase 4 pilot may change (each change logged)
Number of training episodes (same for all conditions), observation feature buckets, α within {0.05, 0.1, 0.2}, ε schedule length.
It may not change: costs, rewards, λ's, ρ levels, metrics, tests, test instances.

## 10. Success threshold (proposal criteria, operationalized)
1 Functional environment: all pytest tests pass. 2 Learning improvement: H0-gate passes. 3 Scarcity sensitivity: H1 rejects
(Friedman) at α = 0.05. 4 Cooperation measurement: C1–C5 computed and validated on scripted episodes. 5 Baseline comparison: H3 reported for
all baselines. 6 Robustness: per-seed plots; principal findings hold in ≥ 8 of 10 seeds. 7 Generalization: test and shifted-test
evaluations reported. 8 Reproducibility: `verify_results.py` exits 0 and the manifest is complete.
Criteria 2, 3 and 6 can fail honestly; a failure is reported as such.

## 11. Freeze record
Frozen on 2026-11-12 after Phase 3 calibration and before any learning run. No IQL code had been executed on any instance when
this document was frozen. Hashes: `results/calibration/freeze_manifest.json`. Changes before the freeze are listed in
`docs/deviations_log.md` (P1–P8); any change from now on is a post-freeze deviation and must be logged there with its reason and
the results it affects.
