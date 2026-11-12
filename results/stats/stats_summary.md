# Phase 6 statistics summary

Unit = training seed (n = 10 per condition unless stated). Values: mean [95% percentile bootstrap CI, 10,000 resamples of seeds]. Paired tests across conditions (seeds matched). Holm corrections within the preregistered families. All 10 seeds analysed; unstable runs included. Performance is after 8,000 training episodes, not converged. The oracle is a full-information reference, never a learner. Families: CONFIRMATORY (preregistered H0-H6), SECONDARY (preregistered, reported without inference or as robustness), EXPLORATORY (unadjusted p), POST HOC (added after seeing results; deviations C4/C5).

### T1. Exp1/Exp2 main sweep, test set, final checkpoint: mean [95% CI] (n = 10; EAR n = 9 at Scarce and Critical)

| level    | rf                   | rescued_heavy_share   | rescued_light_share   | cr                   | ear                  | tdi                  | rsr_other            | pss                  | gini_consumption     |
|:---------|:---------------------|:----------------------|:----------------------|:---------------------|:---------------------|:---------------------|:---------------------|:---------------------|:---------------------|
| Abundant | 0.573 [0.517, 0.627] | 0.422 [0.362, 0.483]  | 0.723 [0.672, 0.770]  | 0.180 [0.155, 0.205] | 0.447 [0.357, 0.547] | 0.607 [0.541, 0.673] | 0.216 [0.163, 0.282] | 0.087 [0.079, 0.095] | 0.073 [0.060, 0.091] |
| Moderate | 0.344 [0.319, 0.368] | 0.221 [0.194, 0.248]  | 0.467 [0.440, 0.493]  | 0.174 [0.158, 0.193] | 0.374 [0.292, 0.475] | 0.545 [0.500, 0.586] | 0.224 [0.157, 0.297] | 0.094 [0.086, 0.102] | 0.090 [0.072, 0.116] |
| Scarce   | 0.180 [0.166, 0.194] | 0.083 [0.055, 0.107]  | 0.277 [0.254, 0.295]  | 0.083 [0.054, 0.111] | 0.505 [0.402, 0.597] | 0.552 [0.499, 0.604] | 0.476 [0.428, 0.534] | 0.077 [0.070, 0.084] | 0.097 [0.068, 0.132] |
| Critical | 0.087 [0.076, 0.098] | 0.016 [0.007, 0.026]  | 0.159 [0.140, 0.174]  | 0.023 [0.010, 0.038] | 0.319 [0.214, 0.429] | 0.461 [0.375, 0.554] | 0.198 [0.138, 0.260] | 0.055 [0.048, 0.061] | 0.085 [0.070, 0.099] |

### T1b. Baselines and oracle reference on the same 100 test instances (oracle = full information, not a learner)

| level    | policy      |    rf |   rescued_heavy_share |    cr |
|:---------|:------------|------:|----------------------:|------:|
| Abundant | random      | 0.063 |                 0.003 | 0.001 |
| Abundant | greedy      | 0.465 |                 0     | 0     |
| Abundant | cooperative | 0.985 |                 0.97  | 0.46  |
| Abundant | oracle      | 1     |                 1     | 0.77  |
| Moderate | oracle      | 0.96  |                 0.92  | 0.726 |
| Moderate | cooperative | 0.707 |                 0.54  | 0.322 |
| Moderate | greedy      | 0.227 |                 0     | 0     |
| Moderate | random      | 0.024 |                 0.001 | 0.001 |
| Scarce   | random      | 0.01  |                 0     | 0     |
| Scarce   | greedy      | 0.123 |                 0     | 0     |
| Scarce   | cooperative | 0.413 |                 0.287 | 0.234 |
| Scarce   | oracle      | 0.617 |                 0.327 | 0.431 |
| Critical | oracle      | 0.403 |                 0.247 | 0.438 |
| Critical | cooperative | 0.233 |                 0.167 | 0.17  |
| Critical | greedy      | 0.075 |                 0     | 0     |
| Critical | random      | 0.005 |                 0     | 0     |

### T2a. H0-gate (CONFIRMATORY)

IQL RF at Abundant vs random (0.063): 10/10 seeds above, one-sided Wilcoxon W+ = 55, exact p = 9.77e-04, δ₁ = 1.00, median difference 0.525. **Gate PASSED.**

### T2b. H1 and H2 (CONFIRMATORY): Friedman and Page's L across the four levels; Holm across the 7 H2 metrics; Kruskal-Wallis = SECONDARY

| family   | metric           |   n_complete | friedman                    |   holm_friedman |   kendall_w |   page_two_sided |   holm_page | trend_direction   |   KW_secondary |
|:---------|:-----------------|-------------:|:----------------------------|----------------:|------------:|-----------------:|------------:|:------------------|---------------:|
| H1       | rf               |           10 | χ²(3) = 30.00, p = 1.38e-06 |        1.38e-06 |       1     |         3.15e-14 |    3.15e-14 | decreasing        |       5.63e-08 |
| H2       | ear              |            8 | χ²(3) = 5.55, p = 0.1357    |        0.407    |       0.231 |         0.2492   |    0.7477   | decreasing        |       0.0771   |
| H2       | rsr              |           10 | χ²(3) = 16.68, p = 8.22e-04 |        0.0041   |       0.556 |         0.0012   |    0.0058   | decreasing        |       3.24e-05 |
| H2       | rsr_other        |           10 | χ²(3) = 12.36, p = 0.0062   |        0.025    |       0.412 |         1        |    1        | increasing        |       0.000292 |
| H2       | tdi              |           10 | χ²(3) = 3.72, p = 0.2933    |        0.5867   |       0.124 |         0.0896   |    0.3582   | decreasing        |       0.1372   |
| H2       | pss              |           10 | χ²(3) = 21.24, p = 9.39e-05 |        0.000563 |       0.708 |         5.93e-06 |    3.56e-05 | decreasing        |       4.37e-05 |
| H2       | gini_consumption |           10 | χ²(3) = 0.60, p = 0.8964    |        0.8964   |       0.02  |         0.6266   |    1        | increasing        |       0.5005   |
| H2       | cr               |           10 | χ²(3) = 24.09, p = 2.39e-05 |        0.000167 |       0.803 |         5.4e-08  |    3.78e-07 | decreasing        |       1.47e-06 |

### T3. Pairwise level comparisons (CONFIRMATORY follow-ups): paired Wilcoxon, Holm across 6 pairs within metric; difference = first minus second level

| family   | metric           | pair                |   n | diff                    |   r_rb |   p_raw |   p_holm6 |   cliffs_delta_secondary |
|:---------|:-----------------|:--------------------|----:|:------------------------|-------:|--------:|----------:|-------------------------:|
| H1       | rf               | Abundant - Moderate |  10 | 0.229 [0.169, 0.292]    |   1    |  0.002  |    0.0117 |                     1    |
| H1       | rf               | Abundant - Scarce   |  10 | 0.393 [0.336, 0.449]    |   1    |  0.002  |    0.0117 |                     1    |
| H1       | rf               | Abundant - Critical |  10 | 0.485 [0.429, 0.543]    |   1    |  0.002  |    0.0117 |                     1    |
| H1       | rf               | Moderate - Scarce   |  10 | 0.164 [0.134, 0.194]    |   1    |  0.002  |    0.0117 |                     1    |
| H1       | rf               | Moderate - Critical |  10 | 0.257 [0.231, 0.283]    |   1    |  0.002  |    0.0117 |                     1    |
| H1       | rf               | Scarce - Critical   |  10 | 0.092 [0.071, 0.114]    |   1    |  0.002  |    0.0117 |                     1    |
| H2       | ear              | Abundant - Moderate |  10 | 0.073 [-0.048, 0.198]   |   0.35 |  0.375  |    1      |                     0.36 |
| H2       | ear              | Abundant - Scarce   |   9 | -0.033 [-0.154, 0.095]  |  -0.16 |  0.7344 |    1      |                    -0.33 |
| H2       | ear              | Abundant - Critical |   9 | 0.096 [-0.022, 0.199]   |   0.64 |  0.0977 |    0.4883 |                     0.49 |
| H2       | ear              | Moderate - Scarce   |   9 | -0.119 [-0.263, 0.072]  |  -0.56 |  0.1641 |    0.6562 |                    -0.42 |
| H2       | ear              | Moderate - Critical |   9 | 0.066 [-0.044, 0.200]   |   0.24 |  0.5703 |    1      |                     0.13 |
| H2       | ear              | Scarce - Critical   |   8 | 0.133 [0.029, 0.237]    |   0.78 |  0.0547 |    0.3281 |                     0.6  |
| H2       | rsr              | Abundant - Moderate |  10 | 0.217 [0.178, 0.266]    |   1    |  0.002  |    0.0117 |                     0.96 |
| H2       | rsr              | Abundant - Scarce   |  10 | 0.069 [-0.014, 0.161]   |   0.38 |  0.3223 |    0.6445 |                     0.48 |
| H2       | rsr              | Abundant - Critical |  10 | 0.258 [0.187, 0.318]    |   1    |  0.002  |    0.0117 |                     0.92 |
| H2       | rsr              | Moderate - Scarce   |  10 | -0.147 [-0.235, -0.056] |  -0.78 |  0.0273 |    0.082  |                    -0.78 |
| H2       | rsr              | Moderate - Critical |  10 | 0.041 [-0.053, 0.126]   |   0.27 |  0.4922 |    0.6445 |                     0.18 |
| H2       | rsr              | Scarce - Critical   |  10 | 0.188 [0.094, 0.282]    |   0.89 |  0.0098 |    0.0391 |                     0.8  |
| H2       | rsr_other        | Abundant - Moderate |  10 | -0.008 [-0.069, 0.049]  |  -0.05 |  0.9219 |    1      |                     0.04 |
| H2       | rsr_other        | Abundant - Scarce   |  10 | -0.260 [-0.338, -0.169] |  -0.96 |  0.0039 |    0.0195 |                    -0.9  |
| H2       | rsr_other        | Abundant - Critical |  10 | 0.018 [-0.060, 0.087]   |   0.2  |  0.625  |    1      |                     0.1  |
| H2       | rsr_other        | Moderate - Scarce   |  10 | -0.252 [-0.357, -0.142] |  -0.89 |  0.0098 |    0.0391 |                    -0.88 |
| H2       | rsr_other        | Moderate - Critical |  10 | 0.026 [-0.055, 0.117]   |   0.16 |  0.6953 |    1      |                     0.16 |
| H2       | rsr_other        | Scarce - Critical   |  10 | 0.278 [0.204, 0.348]    |   1    |  0.002  |    0.0117 |                     0.98 |
| H2       | tdi              | Abundant - Moderate |  10 | 0.062 [-0.020, 0.158]   |   0.2  |  0.625  |    1      |                     0.28 |
| H2       | tdi              | Abundant - Scarce   |  10 | 0.055 [-0.046, 0.151]   |   0.38 |  0.3223 |    0.9668 |                     0.28 |
| H2       | tdi              | Abundant - Critical |  10 | 0.147 [0.027, 0.259]    |   0.67 |  0.0645 |    0.3867 |                     0.56 |
| H2       | tdi              | Moderate - Scarce   |  10 | -0.007 [-0.059, 0.043]  |   0.02 |  1      |    1      |                    -0.04 |
| H2       | tdi              | Moderate - Critical |  10 | 0.084 [-0.002, 0.172]   |   0.53 |  0.1602 |    0.8008 |                     0.38 |
| H2       | tdi              | Scarce - Critical   |  10 | 0.091 [-0.014, 0.198]   |   0.45 |  0.2324 |    0.9297 |                     0.38 |
| H2       | pss              | Abundant - Moderate |  10 | -0.007 [-0.018, 0.005]  |  -0.35 |  0.375  |    0.375  |                    -0.24 |
| H2       | pss              | Abundant - Scarce   |  10 | 0.009 [0.001, 0.017]    |   0.67 |  0.0645 |    0.1289 |                     0.42 |
| H2       | pss              | Abundant - Critical |  10 | 0.032 [0.026, 0.039]    |   1    |  0.002  |    0.0117 |                     0.94 |
| H2       | pss              | Moderate - Scarce   |  10 | 0.017 [0.005, 0.030]    |   0.78 |  0.0273 |    0.082  |                     0.62 |
| H2       | pss              | Moderate - Critical |  10 | 0.039 [0.029, 0.050]    |   1    |  0.002  |    0.0117 |                     1    |
| H2       | pss              | Scarce - Critical   |  10 | 0.023 [0.013, 0.032]    |   0.96 |  0.0039 |    0.0156 |                     0.84 |
| H2       | gini_consumption | Abundant - Moderate |  10 | -0.017 [-0.050, 0.009]  |  -0.35 |  0.375  |    1      |                    -0.42 |
| H2       | gini_consumption | Abundant - Scarce   |  10 | -0.024 [-0.063, 0.009]  |  -0.31 |  0.4316 |    1      |                    -0.26 |
| H2       | gini_consumption | Abundant - Critical |  10 | -0.011 [-0.029, 0.007]  |  -0.42 |  0.2754 |    1      |                    -0.3  |
| H2       | gini_consumption | Moderate - Scarce   |  10 | -0.007 [-0.048, 0.024]  |   0.13 |  0.7695 |    1      |                     0.06 |
| H2       | gini_consumption | Moderate - Critical |  10 | 0.006 [-0.021, 0.040]   |  -0.05 |  0.9219 |    1      |                    -0.12 |
| H2       | gini_consumption | Scarce - Critical   |  10 | 0.012 [-0.022, 0.055]   |  -0.09 |  0.8457 |    1      |                     0.04 |
| H2       | cr               | Abundant - Moderate |  10 | 0.006 [-0.024, 0.037]   |   0.09 |  0.8457 |    0.8457 |                     0.16 |
| H2       | cr               | Abundant - Scarce   |  10 | 0.097 [0.067, 0.123]    |   1    |  0.002  |    0.0117 |                     0.94 |
| H2       | cr               | Abundant - Critical |  10 | 0.157 [0.138, 0.174]    |   1    |  0.002  |    0.0117 |                     1    |
| H2       | cr               | Moderate - Scarce   |  10 | 0.090 [0.054, 0.133]    |   0.96 |  0.0039 |    0.0117 |                     0.94 |
| H2       | cr               | Moderate - Critical |  10 | 0.151 [0.130, 0.169]    |   1    |  0.002  |    0.0117 |                     1    |
| H2       | cr               | Scarce - Critical   |  10 | 0.060 [0.031, 0.088]    |   0.96 |  0.0078 |    0.0156 |                     0.72 |

### T4. H3 (CONFIRMATORY): IQL vs each baseline, one-sample Wilcoxon (two-sided), Holm across 12

| level    | baseline    |   baseline_rf |   iql_mean_rf | diff                    |   n_above |   delta_1 |      p |   p_holm12 |
|:---------|:------------|--------------:|--------------:|:------------------------|----------:|----------:|-------:|-----------:|
| Abundant | random      |         0.063 |         0.573 | 0.510 [0.455, 0.564]    |        10 |       1   | 0.002  |     0.0234 |
| Abundant | greedy      |         0.465 |         0.573 | 0.108 [0.052, 0.162]    |         9 |       0.8 | 0.0137 |     0.0273 |
| Abundant | cooperative |         0.985 |         0.573 | -0.412 [-0.468, -0.358] |         0 |      -1   | 0.002  |     0.0234 |
| Moderate | random      |         0.024 |         0.344 | 0.320 [0.295, 0.344]    |        10 |       1   | 0.002  |     0.0234 |
| Moderate | greedy      |         0.227 |         0.344 | 0.117 [0.092, 0.141]    |        10 |       1   | 0.002  |     0.0234 |
| Moderate | cooperative |         0.707 |         0.344 | -0.362 [-0.387, -0.338] |         0 |      -1   | 0.002  |     0.0234 |
| Scarce   | random      |         0.01  |         0.18  | 0.169 [0.155, 0.184]    |        10 |       1   | 0.002  |     0.0234 |
| Scarce   | greedy      |         0.123 |         0.18  | 0.057 [0.042, 0.071]    |        10 |       1   | 0.002  |     0.0234 |
| Scarce   | cooperative |         0.413 |         0.18  | -0.234 [-0.248, -0.220] |         0 |      -1   | 0.002  |     0.0234 |
| Critical | random      |         0.005 |         0.087 | 0.082 [0.071, 0.093]    |        10 |       1   | 0.002  |     0.0234 |
| Critical | greedy      |         0.075 |         0.087 | 0.012 [0.001, 0.023]    |         7 |       0.5 | 0.0742 |     0.0742 |
| Critical | cooperative |         0.233 |         0.087 | -0.146 [-0.157, -0.135] |         0 |      -1   | 0.002  |     0.0234 |

### T5. H4 and H6 (CONFIRMATORY): paired by seed, Holm across the 4 levels (H6 caveat: solo agents never observed a teammate in training)

| test                          | level    | diff                 |   seeds_in_direction |   r_rb |   p_raw |   p_holm4 |
|:------------------------------|:---------|:---------------------|---------------------:|-------:|--------:|----------:|
| H4 / A1 original - mismatched | Abundant | 0.134 [0.057, 0.211] |                    8 |   0.85 |  0.0137 |    0.0273 |
| H4 / A1 original - mismatched | Moderate | 0.090 [0.067, 0.114] |                   10 |   1    |  0.002  |    0.0078 |
| H4 / A1 original - mismatched | Scarce   | 0.043 [0.025, 0.063] |                   10 |   1    |  0.002  |    0.0078 |
| H4 / A1 original - mismatched | Critical | 0.017 [0.004, 0.030] |                    8 |   0.64 |  0.084  |    0.084  |
| H6 / A4 joint - solo          | Abundant | 0.471 [0.415, 0.527] |                   10 |   1    |  0.002  |    0.0078 |
| H6 / A4 joint - solo          | Moderate | 0.305 [0.280, 0.329] |                   10 |   1    |  0.002  |    0.0078 |
| H6 / A4 joint - solo          | Scarce   | 0.165 [0.150, 0.179] |                   10 |   1    |  0.002  |    0.0078 |
| H6 / A4 joint - solo          | Critical | 0.081 [0.070, 0.091] |                   10 |   1    |  0.002  |    0.0078 |

### T6a. H5 / A3 primary (CONFIRMATORY)

DiD = [RF(Ab) − RF(Cr)]_heavy − [RF(Ab) − RF(Cr)]_all-light (main budgets in both worlds): mean -0.248 [-0.322, -0.171], median -0.219, 0/10 seeds positive, Wilcoxon exact p = 0.0020, r_rb = -1.00. Negative = the all-light world loses MORE rescue-fraction points.

### T6b. A3 difference-in-differences, all analyses (positive = scarcity removes more, in points or log-fraction, in the heavy-victim world); retained = RF(level)/RF(Abundant)

| family                           | analysis                      | level_vs_abundant   | did                     |   seeds_positive |   retained_p05 |   retained_p0 |
|:---------------------------------|:------------------------------|:--------------------|:------------------------|-----------------:|---------------:|--------------:|
| CONFIRMATORY (Critical row = H5) | raw_primary                   | Moderate            | -0.064 [-0.126, 0.004]  |                3 |          0.601 |         0.686 |
| CONFIRMATORY (Critical row = H5) | raw_primary                   | Scarce              | -0.200 [-0.272, -0.129] |                0 |          0.314 |         0.364 |
| CONFIRMATORY (Critical row = H5) | raw_primary                   | Critical            | -0.248 [-0.321, -0.174] |                0 |          0.153 |         0.213 |
| SECONDARY (estimate only)        | oracle_normalised_primary     | Moderate            | -0.078 [-0.141, -0.010] |                2 |          0.626 |         0.686 |
| SECONDARY (estimate only)        | oracle_normalised_primary     | Scarce              | -0.241 [-0.319, -0.168] |                0 |          0.509 |         0.439 |
| SECONDARY (estimate only)        | oracle_normalised_primary     | Critical            | -0.176 [-0.266, -0.081] |                2 |          0.378 |         0.428 |
| SECONDARY (estimate only)        | raw_secondary_own_calibration | Moderate            | -0.170 [-0.235, -0.106] |                1 |          0.601 |         0.487 |
| SECONDARY (estimate only)        | raw_secondary_own_calibration | Scarce              | -0.240 [-0.308, -0.176] |                0 |          0.314 |         0.186 |
| SECONDARY (estimate only)        | raw_secondary_own_calibration | Critical            | -0.207 [-0.273, -0.138] |                1 |          0.153 |         0.109 |
| SECONDARY (estimate only)        | oracle_normalised_secondary   | Moderate            | -0.149 [-0.214, -0.082] |                1 |          0.626 |         0.532 |
| SECONDARY (estimate only)        | oracle_normalised_secondary   | Scarce              | -0.166 [-0.238, -0.098] |                0 |          0.509 |         0.425 |
| SECONDARY (estimate only)        | oracle_normalised_secondary   | Critical            | 0.052 [-0.029, 0.147]   |                6 |          0.378 |         0.609 |
| POST HOC exploratory             | posthoc_log_ratio_primary     | Moderate            | 0.126 [0.003, 0.259]    |                7 |          0.604 |         0.685 |
| POST HOC exploratory             | posthoc_log_ratio_primary     | Scarce              | 0.141 [-0.020, 0.294]   |                8 |          0.315 |         0.363 |
| POST HOC exploratory             | posthoc_log_ratio_primary     | Critical            | 0.331 [0.113, 0.575]    |                8 |          0.151 |         0.21  |
| POST HOC exploratory             | posthoc_log_ratio_secondary   | Moderate            | -0.215 [-0.334, -0.092] |                2 |          0.604 |         0.487 |
| POST HOC exploratory             | posthoc_log_ratio_secondary   | Scarce              | -0.533 [-0.686, -0.390] |                0 |          0.315 |         0.185 |
| POST HOC exploratory             | posthoc_log_ratio_secondary   | Critical            | -0.339 [-0.550, -0.083] |                2 |          0.151 |         0.108 |

### T7. EXPLORATORY paired contrasts (A2, A6, pooled, shifted test); unadjusted p

| analysis                                 | level    |   n |   mean_a |   mean_b | diff                    |   r_rb |   p_unadjusted |
|:-----------------------------------------|:---------|----:|---------:|---------:|:------------------------|-------:|---------------:|
| A2 RF intact - ablated (random)          | Abundant |  10 |    0.573 |    0.389 | 0.184 [0.143, 0.220]    |   1    |         0.002  |
| A2 CR intact - ablated (random)          | Abundant |  10 |    0.18  |    0.09  | 0.090 [0.072, 0.106]    |   1    |         0.002  |
| A2 RF intact - ablated (wait)            | Abundant |  10 |    0.573 |    0.292 | 0.281 [0.244, 0.316]    |   1    |         0.002  |
| A2 CR intact - ablated (wait)            | Abundant |  10 |    0.18  |    0.103 | 0.077 [0.057, 0.095]    |   1    |         0.002  |
| A2 RF intact - ablated (random)          | Moderate |  10 |    0.344 |    0.238 | 0.106 [0.092, 0.120]    |   1    |         0.002  |
| A2 CR intact - ablated (random)          | Moderate |  10 |    0.174 |    0.08  | 0.094 [0.081, 0.109]    |   1    |         0.002  |
| A2 RF intact - ablated (wait)            | Moderate |  10 |    0.344 |    0.19  | 0.154 [0.135, 0.173]    |   1    |         0.002  |
| A2 CR intact - ablated (wait)            | Moderate |  10 |    0.174 |    0.101 | 0.073 [0.062, 0.083]    |   1    |         0.002  |
| A2 RF intact - ablated (random)          | Scarce   |  10 |    0.18  |    0.122 | 0.058 [0.051, 0.064]    |   1    |         0.002  |
| A2 CR intact - ablated (random)          | Scarce   |  10 |    0.083 |    0.034 | 0.049 [0.031, 0.066]    |   1    |         0.0039 |
| A2 RF intact - ablated (wait)            | Scarce   |  10 |    0.18  |    0.095 | 0.084 [0.075, 0.093]    |   1    |         0.002  |
| A2 CR intact - ablated (wait)            | Scarce   |  10 |    0.083 |    0.039 | 0.044 [0.028, 0.059]    |   1    |         0.0039 |
| A2 RF intact - ablated (random)          | Critical |  10 |    0.087 |    0.066 | 0.022 [0.017, 0.026]    |   1    |         0.002  |
| A2 CR intact - ablated (random)          | Critical |  10 |    0.023 |    0.009 | 0.014 [0.006, 0.024]    |   1    |         0.0078 |
| A2 RF intact - ablated (wait)            | Critical |  10 |    0.087 |    0.049 | 0.038 [0.032, 0.043]    |   1    |         0.002  |
| A2 CR intact - ablated (wait)            | Critical |  10 |    0.023 |    0.011 | 0.012 [0.006, 0.019]    |   1    |         0.0078 |
| A6 RF equal-steps - equal-episodes       | Moderate |  10 |    0.422 |    0.344 | 0.078 [0.036, 0.116]    |   0.89 |         0.0098 |
| A6 RF equal-steps - equal-episodes       | Scarce   |  10 |    0.145 |    0.18  | -0.034 [-0.066, -0.003] |  -0.64 |         0.0781 |
| A6 RF equal-steps - equal-episodes       | Critical |  10 |    0.104 |    0.087 | 0.016 [-0.009, 0.043]   |   0.31 |         0.4316 |
| Pooled - per-agent RF                    | Abundant |  10 |    0.667 |    0.573 | 0.095 [0.014, 0.187]    |   0.53 |         0.1602 |
| Pooled - per-agent RF                    | Moderate |  10 |    0.405 |    0.344 | 0.061 [0.032, 0.090]    |   0.93 |         0.0059 |
| Pooled - per-agent RF                    | Scarce   |  10 |    0.195 |    0.18  | 0.015 [-0.004, 0.038]   |   0.38 |         0.3223 |
| Pooled - per-agent RF                    | Critical |  10 |    0.129 |    0.087 | 0.042 [0.023, 0.066]    |   1    |         0.002  |
| Shifted test - same-distribution test RF | Abundant |  10 |    0.429 |    0.573 | -0.144 [-0.164, -0.124] |  -1    |         0.002  |
| Shifted test - same-distribution test RF | Moderate |  10 |    0.256 |    0.344 | -0.088 [-0.107, -0.071] |  -1    |         0.002  |
| Shifted test - same-distribution test RF | Scarce   |  10 |    0.139 |    0.18  | -0.041 [-0.050, -0.032] |  -1    |         0.002  |
| Shifted test - same-distribution test RF | Critical |  10 |    0.079 |    0.087 | -0.008 [-0.012, -0.004] |  -0.93 |         0.0059 |

### T8. Scarcity trend in robustness variants (EXPLORATORY) and best-validation sensitivity (SECONDARY)

| analysis                                  |   friedman_chi2 |   friedman_p |   kendall_w |   page_two_sided_p | direction   |
|:------------------------------------------|----------------:|-------------:|------------:|-------------------:|:------------|
| A6_equal_steps_trend                      |           26.4  |     7.86e-06 |       0.88  |           8.01e-10 | decreasing  |
| trend_pooled                              |           28.92 |     2.33e-06 |       0.964 |           9.78e-13 | decreasing  |
| trend_alt                                 |           28.08 |     3.49e-06 |       0.936 |           1.41e-11 | decreasing  |
| trend_p0                                  |           30    |     1.38e-06 |       1     |           3.15e-14 | decreasing  |
| trend_p0sec                               |           30    |     1.38e-06 |       1     |           3.15e-14 | decreasing  |
| trend_shifted                             |           30    |     1.38e-06 |       1     |           3.15e-14 | decreasing  |
| SECONDARY best-validation checkpoint (H1) |           30    |     1.38e-06 |       1     |           3.15e-14 | decreasing  |

### T9. Stable-run sensitivity (SECONDARY)

5 of 350 training runs meet the preregistered stability criterion; main block: 0 of 40. not computable: 0 of 40 main-block runs meet the preregistered stability criterion. Stable runs by block: eqsteps/Moderate 2, eqsteps/Scarce 1, p0sec/Critical 1, pooled/Moderate 1.

### T10. A8 (EXPLORATORY, observational association): OLS of seed RF on standardized metrics + level dummies; cluster bootstrap over seeds. n = 38 (excluded 2 with undefined EAR); R² levels only 0.927, joint 0.978; VIF ear 1.4, rsr_other 1.3, tdi 1.7, pss 7.8, gini_consumption 1.4, cr 8.3

| model   | term             | coef_ci                    | within_level_spearman                                         |
|:--------|:-----------------|:---------------------------|:--------------------------------------------------------------|
| joint   | intercept        | 0.5306 [0.4812, 0.5889]    |                                                               |
| joint   | ear              | -0.0027 [-0.0235, 0.0081]  |                                                               |
| joint   | rsr_other        | -0.0006 [-0.0178, 0.0275]  |                                                               |
| joint   | tdi              | -0.0022 [-0.0272, 0.0214]  |                                                               |
| joint   | pss              | 0.0455 [0.0143, 0.0738]    |                                                               |
| joint   | gini_consumption | -0.0126 [-0.0279, 0.0088]  |                                                               |
| joint   | cr               | 0.0261 [-0.0163, 0.0913]   |                                                               |
| joint   | level_Moderate   | -0.2407 [-0.2880, -0.2013] |                                                               |
| joint   | level_Scarce     | -0.3311 [-0.4252, -0.2408] |                                                               |
| joint   | level_Critical   | -0.3518 [-0.4613, -0.2347] |                                                               |
| single  | ear              | 0.0172 [-0.0008, 0.0290]   | Abundant:0.333;Moderate:0.576;Scarce:0.000;Critical:-0.217    |
| single  | rsr_other        | -0.0223 [-0.0387, -0.0047] | Abundant:-0.576;Moderate:-0.236;Scarce:0.167;Critical:-0.017  |
| single  | tdi              | -0.0260 [-0.0456, -0.0112] | Abundant:-0.697;Moderate:0.103;Scarce:-0.633;Critical:-0.917  |
| single  | pss              | 0.0650 [0.0456, 0.0906]    | Abundant:0.952;Moderate:0.952;Scarce:0.800;Critical:0.400     |
| single  | gini_consumption | -0.0200 [-0.0615, -0.0045] | Abundant:-0.855;Moderate:-0.212;Scarce:-0.617;Critical:-0.583 |
| single  | cr               | 0.0824 [0.0537, 0.1200]    | Abundant:0.952;Moderate:0.733;Scarce:0.450;Critical:0.283     |

### T11. Exp4 individual vs collective (EXPLORATORY): E1 abandonment and E2 duplicate rescues per episode; E3 conflict share; Spearman of best individual vs collective return across episodes

| level    | measure                                             | value                |
|:---------|:----------------------------------------------------|:---------------------|
| Abundant | e1                                                  | 3.337 [2.641, 4.197] |
| Abundant | e2                                                  | 0.362 [0.227, 0.509] |
| Abundant | e3                                                  | 0.161 [0.140, 0.183] |
| Abundant | spearman(best individual return, collective return) | 0.954                |
| Moderate | e1                                                  | 1.693 [1.263, 2.094] |
| Moderate | e2                                                  | 0.120 [0.068, 0.180] |
| Moderate | e3                                                  | 0.148 [0.118, 0.178] |
| Moderate | spearman(best individual return, collective return) | 0.957                |
| Scarce   | e1                                                  | 0.372 [0.246, 0.507] |
| Scarce   | e2                                                  | 0.067 [0.036, 0.103] |
| Scarce   | e3                                                  | 0.209 [0.185, 0.235] |
| Scarce   | spearman(best individual return, collective return) | 0.947                |
| Critical | e1                                                  | 0.152 [0.074, 0.255] |
| Critical | e2                                                  | 0.024 [0.008, 0.045] |
| Critical | e3                                                  | 0.052 [0.035, 0.071] |
| Critical | spearman(best individual return, collective return) | 0.953                |

### T12. Exp5 cross-ρ transfer matrix (EXPLORATORY): rows trained at, columns tested at, mean RF [95% CI]

| train_level   | Abundant             | Moderate             | Scarce               | Critical             |
|:--------------|:---------------------|:---------------------|:---------------------|:---------------------|
| Abundant      | 0.573 [0.517, 0.627] | 0.192 [0.151, 0.235] | 0.072 [0.052, 0.096] | 0.010 [0.007, 0.013] |
| Moderate      | 0.161 [0.151, 0.171] | 0.344 [0.319, 0.368] | 0.207 [0.200, 0.213] | 0.116 [0.101, 0.128] |
| Scarce        | 0.059 [0.054, 0.064] | 0.169 [0.153, 0.186] | 0.180 [0.165, 0.194] | 0.121 [0.112, 0.130] |
| Critical      | 0.049 [0.047, 0.052] | 0.106 [0.097, 0.115] | 0.100 [0.089, 0.112] | 0.087 [0.076, 0.098] |
