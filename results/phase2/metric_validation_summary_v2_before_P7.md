# Phase 2 metric construct-validity check — v2: C2 fix applied, cooperative search convention (P7) DISABLED (regenerated for the record)

**Not an experimental result.** Uncalibrated placeholder budgets (b0) and horizon H = 200; 50 validation instances; deterministic baselines; ratio metrics pooled over episodes (sum of numerators / sum of denominators). The oracle is a full-information centralized REFERENCE, shown for context only.

| budget    | policy      |   episodes |    rf |   heavy_rescued |     ear |     rsr |   rsr_other |   tdi |   pss |   gini_consumption |    cr |   collective_return |
|:----------|:------------|-----------:|------:|----------------:|--------:|--------:|------------:|------:|------:|-------------------:|------:|--------------------:|
| unlimited | random      |         50 | 0.237 |               0 |   0.000 |   0.981 |       0.846 | 0.611 | 0.007 |              0.020 | 0.000 |              -6.596 |
| unlimited | greedy      |         50 | 0.500 |               0 | nan     |   0.667 |       0.667 | 0.000 | 0.040 |              0.000 | 0.000 |               8.106 |
| unlimited | cooperative |         50 | 1.000 |             150 |   0.877 |   0.467 |       0.467 | 0.692 | 0.178 |              0.085 | 0.474 |              21.910 |
| unlimited | oracle      |         50 | 1.000 |             150 |   1.000 | nan     |     nan     | 0.754 | 0.328 |              0.276 | 0.792 |              23.135 |
| b0=40     | random      |         50 | 0.037 |               0 | nan     |   0.927 |       0.825 | 0.644 | 0.006 |              0.010 | 0.000 |              -1.207 |
| b0=40     | greedy      |         50 | 0.327 |               0 | nan     |   0.667 |       0.667 | 0.000 | 0.051 |              0.000 | 0.000 |               5.954 |
| b0=40     | cooperative |         50 | 0.827 |             103 |   0.798 |   0.463 |       0.463 | 0.744 | 0.166 |              0.025 | 0.353 |              18.143 |
| b0=40     | oracle      |         50 | 1.000 |             150 |   1.000 | nan     |     nan     | 0.716 | 0.319 |              0.194 | 0.754 |              23.096 |
| b0=20     | random      |         50 | 0.020 |               0 | nan     |   0.877 |       0.806 | 0.689 | 0.006 |              0.021 | 0.000 |              -0.512 |
| b0=20     | greedy      |         50 | 0.150 |               0 | nan     |   0.667 |       0.667 | 0.000 | 0.049 |              0.000 | 0.000 |               2.701 |
| b0=20     | cooperative |         50 | 0.423 |              37 |   0.755 |   0.488 |       0.488 | 0.768 | 0.158 |              0.019 | 0.210 |               9.457 |
| b0=20     | oracle      |         50 | 0.653 |              56 |   1.000 | nan     |     nan     | 0.730 | 0.317 |              0.161 | 0.482 |              15.248 |

## Pre-stated checks

| check | budget | detail | result |
|---|---|---|---|
| X1 | unlimited | cooperative ear 0.877 > random 0.000 | PASS |
| X1 | unlimited | cooperative ear 0.877 > greedy nan (other undefined: no ASSIST at all) | PASS |
| X1 | unlimited | cooperative tdi 0.692 > random 0.611 | PASS |
| X1 | unlimited | cooperative tdi 0.692 > greedy 0.000 | PASS |
| X1 | unlimited | cooperative cr 0.474 > random 0.000 | PASS |
| X1 | unlimited | cooperative cr 0.474 > greedy 0.000 | PASS |
| X2 | unlimited | cooperative rsr_other 0.467 < random 0.846 | PASS |
| X2 | unlimited | cooperative rsr_other 0.467 < greedy 0.667 | PASS |
| X3 | unlimited | greedy cr = 0.000, heavy rescued = 0 | PASS |
| X4 | unlimited | Spearman(collective_return, ear) = 0.136 (n = 54) | PASS |
| X4 | unlimited | Spearman(collective_return, rsr_other) = -0.881 (n = 124) | PASS |
| X4 | unlimited | Spearman(collective_return, tdi) = 0.252 (n = 150) | PASS |
| X4 | unlimited | Spearman(collective_return, pss) = 1.000 (n = 150) | FAIL |
| X4 | unlimited | Spearman(collective_return, gini_consumption) = 0.409 (n = 150) | PASS |
| X4 | unlimited | Spearman(collective_return, cr) = 0.822 (n = 150) | PASS |
| X1 | b0=40 | cooperative ear 0.798 > random nan (other undefined: no ASSIST at all) | PASS |
| X1 | b0=40 | cooperative ear 0.798 > greedy nan (other undefined: no ASSIST at all) | PASS |
| X1 | b0=40 | cooperative tdi 0.744 > random 0.644 | PASS |
| X1 | b0=40 | cooperative tdi 0.744 > greedy 0.000 | PASS |
| X1 | b0=40 | cooperative cr 0.353 > random 0.000 | PASS |
| X1 | b0=40 | cooperative cr 0.353 > greedy 0.000 | PASS |
| X2 | b0=40 | cooperative rsr_other 0.463 < random 0.825 | PASS |
| X2 | b0=40 | cooperative rsr_other 0.463 < greedy 0.667 | PASS |
| X3 | b0=40 | greedy cr = 0.000, heavy rescued = 0 | PASS |
| X4 | b0=40 | Spearman(collective_return, ear) = 0.131 (n = 50) | PASS |
| X4 | b0=40 | Spearman(collective_return, rsr_other) = -0.800 (n = 123) | PASS |
| X4 | b0=40 | Spearman(collective_return, tdi) = 0.237 (n = 150) | PASS |
| X4 | b0=40 | Spearman(collective_return, pss) = 0.983 (n = 150) | FAIL |
| X4 | b0=40 | Spearman(collective_return, gini_consumption) = 0.182 (n = 150) | PASS |
| X4 | b0=40 | Spearman(collective_return, cr) = 0.822 (n = 150) | PASS |
| X1 | b0=20 | cooperative ear 0.755 > random nan (other undefined: no ASSIST at all) | PASS |
| X1 | b0=20 | cooperative ear 0.755 > greedy nan (other undefined: no ASSIST at all) | PASS |
| X1 | b0=20 | cooperative tdi 0.768 > random 0.689 | PASS |
| X1 | b0=20 | cooperative tdi 0.768 > greedy 0.000 | PASS |
| X1 | b0=20 | cooperative cr 0.210 > random 0.000 | PASS |
| X1 | b0=20 | cooperative cr 0.210 > greedy 0.000 | PASS |
| X2 | b0=20 | cooperative rsr_other 0.488 < random 0.806 | PASS |
| X2 | b0=20 | cooperative rsr_other 0.488 < greedy 0.667 | PASS |
| X3 | b0=20 | greedy cr = 0.000, heavy rescued = 0 | PASS |
| X4 | b0=20 | Spearman(collective_return, ear) = 0.412 (n = 30) | PASS |
| X4 | b0=20 | Spearman(collective_return, rsr_other) = -0.743 (n = 121) | PASS |
| X4 | b0=20 | Spearman(collective_return, tdi) = 0.250 (n = 150) | PASS |
| X4 | b0=20 | Spearman(collective_return, pss) = 0.948 (n = 150) | PASS |
| X4 | b0=20 | Spearman(collective_return, gini_consumption) = -0.026 (n = 150) | PASS |
| X4 | b0=20 | Spearman(collective_return, cr) = 0.612 (n = 150) | PASS |

**43/45 checks passed.**

## Oracle reference vs exhaustive macro-plan optimum (tiny instances: 6x6, V = 3, b0 in {5, 8, 12})

300 cases; oracle equals the optimum in 297 (99.0%); total rescues oracle 370 vs optimum 373 (99.2%); max gap 1.
