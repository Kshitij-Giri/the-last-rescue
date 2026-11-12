# Phase 6 — Statistical analysis, figures and verification (summary)

Scope: frozen preregistration v1.0. All 10 confirmatory seeds; unstable runs included; performance after 8,000 training
episodes (not converged). Inputs: raw test-episode CSVs (results/eval), never summaries. Full tables:
`results/stats/stats_summary.md`, `results/tables/`; figures: `results/figures/`; claim checks: `docs/claims_ledger.md`;
verification log: `results/logs/verify_results.txt` (272/272 checks passed, including 72/72 claim checks). Analysis decisions: D26; deviations C3–C6.
Values are mean [95% percentile bootstrap CI over seeds]. CIs are unadjusted; inference uses the preregistered tests.

## A1–A8 status

| Item | Status | Where |
|---|---|---|
| A1 teammate mismatch (H4) | Complete, confirmatory test | T5, Fig. 4 |
| A2 agent ablation | Complete, exploratory | T7, Fig. 4, a2_cooperative_baseline.csv |
| A3 cooperation-necessary vs optional (H5) | Complete: primary test; secondary (a) own calibration and (b) oracle-normalised; 4-level curves; post hoc log scale | T6, Fig. 5 |
| A4 solo-learner control (H6) | Complete, confirmatory test (with distribution-shift caveat) | T5, Fig. 4 |
| A5 non-stationarity diagnostics | Complete: churn, TD error, curves, stability counts; stable-run sensitivity reported (not computable for the main block) | Fig. 1, Fig. 7, T9 |
| A6 equal environment steps | Complete, exploratory paired contrasts + trend test | T7, T8, Fig. 4 |
| A7 statistics | Complete: H0–H6 with Friedman/Page/Wilcoxon, Holm families, rank-biserial r, Kendall's W, bootstrap CIs; secondary Kruskal–Wallis and Cliff's δ | T2–T6 |
| A8 mediation | Complete, observational association only | T10, Fig. 8 |

## Confirmatory results

- **H0 gate: passed.** 10/10 seeds above random at Abundant; exact one-sided p = 0.00098; δ₁ = 1.00.
- **H1 (rescue fraction across ρ): significant, perfectly ordered.** Friedman χ²(3) = 30.0, p = 1.4e-6, Kendall's W = 1.00
  (every seed ranks Abundant > Moderate > Scarce > Critical); Page two-sided p = 3.2e-14; all 6 pairwise contrasts Holm
  p = 0.0117 (the smallest attainable with 10 seeds and 6 tests). RF 0.573 → 0.344 → 0.180 → 0.087.
- **H2 (cooperation metrics; Holm across 7):** significant change for C5 cooperation rate (Holm p = 0.00017; 0.180 →
  0.023, decreasing), C4a PSS (0.00056; reported only with its reward-tracking caveat, D22), C2 RSR (0.0041) and C2
  RSR_other (0.025; non-monotone: peaks at Scarce, Page Holm p = 1). Not significant: C1 effective-assist rate (0.41,
  n = 8 complete seeds), C3 territory division (0.59), C4b consumption Gini (0.90).
- **H3 (vs baselines; Holm across 12):** IQL > random at every level; IQL > greedy at Abundant, Moderate and Scarce
  (Holm p ≤ 0.027) but **not at Critical** (Holm p = 0.074; 7 seeds above, 2 below, 1 exactly tied); IQL < cooperative
  baseline at every level.
- **H4 (A1 mismatch; Holm across 4):** original teams beat mismatched teams at Abundant (0.134, Holm p = 0.027),
  Moderate (0.090, 0.0078) and Scarce (0.043, 0.0078); not at Critical (0.017, Holm p = 0.084). The relative loss is
  about 20–26% at every level: co-adapted conventions exist and matter wherever performance is above the floor.
- **H5 (A3 primary DiD): significant, negative.** −0.248 [−0.322, −0.171], 0/10 seeds positive, exact p = 0.0020: the
  all-light world loses more rescue-fraction points from Abundant to Critical (0.733) than the heavy-victim world (0.485).
- **H6 (A4 joint vs solo; Holm across 4):** joint training beats solo training at every level (Abundant 0.471, Holm
  p = 0.0078 everywhere; 10/10 seeds).

## What the oracle-normalised A3 analysis changes (point 3 of the Phase 6 brief)

- The preregistered secondary DiD on oracle-normalised RF (RF / oracle reference RF in the same world and budget) is still
  negative at every level: Critical −0.176 [−0.266, −0.081]. Normalising by "what was achievable" therefore does **not**
  reverse the sign of the raw DiD. The raw result is not merely an artefact of different achievable ceilings.
- But both are additive contrasts. On a proportional scale the picture flips: the heavy-victim world keeps 15% of its
  Abundant RF at Critical, the all-light world 21%. The post hoc log-scale DiD of drops (deviations C4/C5, exploratory)
  is +0.331 [+0.113, +0.575]: scarcity removes a larger **fraction** of performance when cooperation is needed.
- The world-specific calibration (secondary a) gives a different answer again (oracle-normalised DiD at Critical +0.052
  [−0.029, +0.148]; post hoc log-scale −0.339), because there the all-light world's own Critical budget is harsher.
- Interpretation: the claim "scarcity hurts more when cooperation is required" is **not supported on the preregistered
  absolute scale**: there it points the other way, and that is robust to oracle normalisation. A proportional reading
  supports it, and the comparison depends on how scarcity is calibrated. The defensible statement is that the
  interaction is scale- and calibration-dependent. The robust finding is that cooperative (heavy) rescues collapse fastest
  within the heavy-victim world (heavy share 0.422 → 0.016 vs light 0.723 → 0.159).

## Secondary and exploratory results (no confirmatory weight)

- **Stability (A5):** 5 of 350 runs meet the stability criterion; 0 of 40 main-block runs. The preregistered "stable runs
  only" repetition of H1 is therefore not computable. Churn stays above 5% and TD error still rises at 8,000 episodes
  (Fig. 7).
- **Best-validation checkpoint:** identical perfect ordering (W = 1.00); Abundant RF 0.647 vs 0.573 (final).
- **A6 equal steps:** the scarcity trend persists (Page p = 8.0e-10). More data helps at Moderate (+0.078, p = 0.0098
  unadjusted) but not at Scarce (−0.035) or Critical (+0.017): the scarcity effect is not explained by fewer transitions.
- **A2 ablation:** replacing one agent lowers RF at every level (Abundant: −0.184 random, −0.281 WAIT-only); the WAIT-only
  replacement hurts learned teams more than a random one.
- **Robustness:** the trend holds with a pooled budget, on the 12×12 map, in both all-light worlds and on the shifted test
  set (all Page p < 1e-10). The pooled budget raises RF at Moderate (+0.061) and Critical (+0.042).
- **Exp5:** the shifted test lowers RF (Abundant 0.429 vs 0.573). Transfer: Abundant-trained policies collapse at Critical
  (0.010). Scarce-trained (0.121) and Moderate-trained (0.116) policies beat Critical-trained ones (0.087) at Critical.
- **Exp4:** individual and collective returns are strongly aligned (Spearman ≈ 0.95 at every level); E3 conflicts
  5–21% of episodes; E1 abandonment falls from 3.3 to 0.15 per episode as joint attempts disappear.
- **A8 (association only):** with level dummies alone R² = 0.927; adding the six metrics gives 0.978. In one-metric models,
  C5 cooperation rate (+0.082 per SD [0.054, 0.120]) and C4a are positively associated with RF within levels, and C2
  RSR_other, C3 TDI and C4b Gini negatively. In the joint model only C4a's CI excludes zero; C5 and C4a are collinear
  (VIF ≈ 8). C4a tracks reward by construction, so this does not identify cooperation as a mediator. The causal evidence
  that cooperation matters comes from A1, A2 and A4 (with their caveats), not from A8.

## Limitations (carried into the report)

1. Not converged: 5/350 stable runs; conclusions are about learning after 8,000 episodes.
2. A3 is scale- and calibration-dependent (above).
3. A4 mixes coordination learning with observation distribution shift (solo agents never saw a teammate).
4. Abundant is mostly time-limited for learned teams (episodes end at the horizon).
5. Greedy agents move in lockstep (D22), so "IQL > greedy" means "better than uncoordinated identical agents".
6. C4a tracks reward (D22). C1 is undefined for two seed-levels (complete-block n = 8).
7. Ten seeds: the smallest attainable p-values (0.002 two-sided; Holm 0.0117 across 6) bound the evidence. Bootstrap CIs
   are unadjusted and can exclude zero where a corrected test does not (H3 and H4 at Critical).
8. Small-map limitation from calibration (Phase 3): conclusions at Scarce/Critical do not transfer to 8×8 maps.

## Verification

`python scripts/verify_results.py` → 272 checks passed, 0 failed:
- independent recomputation of every seed-level value from the raw episodes;
- direct-scipy recomputation of all confirmatory statistics and Holm adjustments;
- byte-identical re-run of the whole statistics pipeline (18/18 files);
- 72/72 claims in `docs/claims.yaml` verified against their sources (V5);
- 350 training runs;
- 67/67 raw evaluation files unchanged since the Phase 5 manifest.

Two problems were found and fixed during Phase 6:
- **C5:** a sign-convention error in the post hoc log-scale DiD, caught while inspecting Fig. 5.
- **C6:** floating-point tie handling in the Wilcoxon tests, caught by the verifier. It changed the H3 Critical-vs-greedy
  p-value from 0.084 to 0.074; the conclusion is unchanged.

All 8 replays re-simulate their test episodes and reproduce the recorded rows exactly (`results/replays/phase6_index.csv`).

Count note: 272 = 200 non-claim checks (V1–V4, V6) + 72 claim checks (V5). An earlier draft of this summary quoted 262 and
62, the counts before 10 further claims were added to the ledger; the verifier output was always the authoritative source.
