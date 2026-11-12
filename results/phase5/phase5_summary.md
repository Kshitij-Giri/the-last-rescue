# Phase 5 results summary (descriptive; formal analysis is Phase 6)

All values are on the frozen **test** instances (100 per condition; shifted test where stated), after **8,000 training episodes** (not converged; Phase 4). Unit = training seed (0-9): per seed, mean over test episodes, ratio metrics pooled. All runs are included, stable or not. The oracle is a full-information centralized reference, never a learner.

## Training runs and stability (A5)

350 training runs completed, 4.48 CPU-hours of training. Stable = preregistered criterion (churn < 5% between the last two checkpoints and validation RF range < 0.02 over the last three).

| block   | level    |   runs |   stable |   churn_mean |   rf_range_mean |   episodes_mean |   env_steps_mean |   cpu_seconds |
|:--------|:---------|-------:|---------:|-------------:|----------------:|----------------:|-----------------:|--------------:|
| main    | Abundant |     10 |        0 |        0.126 |           0.133 |        8000.000 |       709302.600 |       984.800 |
| main    | Moderate |     10 |        0 |        0.050 |           0.051 |        8000.000 |       480853.900 |       667.100 |
| main    | Scarce   |     10 |        0 |        0.058 |           0.030 |        8000.000 |       296432.400 |       426.300 |
| main    | Critical |     10 |        0 |        0.092 |           0.032 |        8000.000 |       254122.600 |       363.300 |
| p0      | Abundant |     10 |        0 |        0.113 |           0.077 |        8000.000 |       535590.800 |       710.800 |
| p0      | Moderate |     10 |        0 |        0.078 |           0.053 |        8000.000 |       387263.900 |       520.100 |
| p0      | Scarce   |     10 |        0 |        0.082 |           0.044 |        8000.000 |       229929.200 |       320.100 |
| p0      | Critical |     10 |        0 |        0.106 |           0.044 |        8000.000 |       189738.500 |       265.700 |
| p0sec   | Abundant |     10 |        0 |        0.067 |           0.050 |        8000.000 |       353005.100 |       469.300 |
| p0sec   | Moderate |     10 |        0 |        0.070 |           0.036 |        8000.000 |       244208.100 |       326.600 |
| p0sec   | Scarce   |     10 |        0 |        0.084 |           0.016 |        8000.000 |       157060.300 |       219.100 |
| p0sec   | Critical |     10 |        1 |        0.100 |           0.011 |        8000.000 |       132807.900 |       185.800 |
| pooled  | Abundant |     10 |        0 |        0.090 |           0.070 |        8000.000 |       631912.800 |       846.500 |
| pooled  | Moderate |     10 |        1 |        0.049 |           0.046 |        8000.000 |       355174.000 |       491.700 |
| pooled  | Scarce   |     10 |        0 |        0.080 |           0.032 |        8000.000 |       229352.900 |       328.000 |
| pooled  | Critical |     10 |        0 |        0.098 |           0.021 |        8000.000 |       181398.100 |       262.700 |
| alt     | Abundant |     10 |        0 |        0.218 |           0.200 |        8000.000 |      1019684.800 |      1333.500 |
| alt     | Moderate |     10 |        0 |        0.065 |           0.099 |        8000.000 |       684934.600 |       926.200 |
| alt     | Scarce   |     10 |        0 |        0.070 |           0.039 |        8000.000 |       407649.700 |       576.500 |
| alt     | Critical |     10 |        0 |        0.114 |           0.030 |        8000.000 |       358989.300 |       506.300 |
| solo    | Abundant |     30 |        0 |        0.487 |           0.067 |        8000.000 |       538072.333 |      1144.500 |
| solo    | Moderate |     30 |        0 |        0.371 |           0.069 |        8000.000 |       273543.467 |       611.900 |
| solo    | Scarce   |     30 |        0 |        0.248 |           0.047 |        8000.000 |       146527.267 |       334.200 |
| solo    | Critical |     30 |        0 |        0.231 |           0.039 |        8000.000 |        98795.233 |       234.500 |
| eqsteps | Moderate |     10 |        2 |        0.043 |           0.047 |       15539.400 |       709335.100 |       992.600 |
| eqsteps | Scarce   |     10 |        1 |        0.102 |           0.050 |       25527.000 |       709348.900 |      1027.100 |
| eqsteps | Critical |     10 |        0 |        0.081 |           0.045 |       33225.800 |       709332.200 |      1054.800 |

## Exp1 / Exp2 — main sweep, seed level (final checkpoint, test)

**Abundant**

|   seed |    rf |   rescued_heavy_share |   rescued_light_share |   ear |   rsr_other |   tdi |   pss |    cr |   e1_abandonment |   steps |   exhausted |   horizon |
|-------:|------:|----------------------:|----------------------:|------:|------------:|------:|------:|------:|-----------------:|--------:|------------:|----------:|
|      0 | 0.502 |                 0.317 |                 0.687 | 0.408 |       0.207 | 0.735 | 0.076 | 0.140 |            2.050 | 103.510 |       0.000 |     0.980 |
|      1 | 0.595 |                 0.453 |                 0.737 | 0.687 |       0.153 | 0.641 | 0.090 | 0.197 |            2.400 | 101.240 |       0.010 |     0.940 |
|      2 | 0.580 |                 0.437 |                 0.723 | 0.736 |       0.244 | 0.736 | 0.089 | 0.183 |            3.240 |  98.860 |       0.020 |     0.900 |
|      3 | 0.653 |                 0.523 |                 0.783 | 0.480 |       0.101 | 0.429 | 0.105 | 0.232 |            1.920 | 101.400 |       0.010 |     0.940 |
|      4 | 0.722 |                 0.587 |                 0.857 | 0.424 |       0.129 | 0.485 | 0.107 | 0.242 |            3.950 |  91.220 |       0.070 |     0.750 |
|      5 | 0.405 |                 0.260 |                 0.550 | 0.227 |       0.268 | 0.663 | 0.065 | 0.113 |            3.800 | 102.680 |       0.010 |     0.960 |
|      6 | 0.510 |                 0.343 |                 0.677 | 0.369 |       0.174 | 0.735 | 0.079 | 0.151 |            2.700 | 102.760 |       0.020 |     0.960 |
|      7 | 0.653 |                 0.527 |                 0.780 | 0.302 |       0.246 | 0.516 | 0.093 | 0.219 |            6.570 |  93.790 |       0.120 |     0.780 |
|      8 | 0.508 |                 0.350 |                 0.667 | 0.349 |       0.462 | 0.529 | 0.076 | 0.149 |            3.800 | 100.920 |       0.030 |     0.930 |
|      9 | 0.598 |                 0.427 |                 0.770 | 0.490 |       0.176 | 0.604 | 0.087 | 0.175 |            2.940 |  99.720 |       0.040 |     0.900 |

**Moderate**

|   seed |    rf |   rescued_heavy_share |   rescued_light_share |   ear |   rsr_other |   tdi |   pss |    cr |   e1_abandonment |   steps |   exhausted |   horizon |
|-------:|------:|----------------------:|----------------------:|------:|------------:|------:|------:|------:|-----------------:|--------:|------------:|----------:|
|      0 | 0.275 |                 0.140 |                 0.410 | 0.284 |       0.285 | 0.560 | 0.075 | 0.139 |            1.360 |  90.350 |       0.200 |     0.800 |
|      1 | 0.385 |                 0.237 |                 0.533 | 0.401 |       0.324 | 0.651 | 0.104 | 0.171 |            1.490 |  78.560 |       0.360 |     0.640 |
|      2 | 0.387 |                 0.270 |                 0.503 | 0.279 |       0.140 | 0.397 | 0.101 | 0.194 |            2.430 |  67.090 |       0.500 |     0.490 |
|      3 | 0.352 |                 0.213 |                 0.490 | 0.379 |       0.118 | 0.545 | 0.091 | 0.171 |            1.970 |  65.470 |       0.530 |     0.470 |
|      4 | 0.300 |                 0.187 |                 0.413 | 0.218 |       0.175 | 0.537 | 0.082 | 0.142 |            2.620 |  77.860 |       0.370 |     0.630 |
|      5 | 0.340 |                 0.233 |                 0.447 | 0.278 |       0.408 | 0.578 | 0.096 | 0.174 |            2.260 |  84.160 |       0.280 |     0.720 |
|      6 | 0.380 |                 0.257 |                 0.503 | 0.606 |       0.107 | 0.464 | 0.101 | 0.180 |            0.780 |  75.470 |       0.410 |     0.590 |
|      7 | 0.303 |                 0.197 |                 0.410 | 0.304 |       0.130 | 0.532 | 0.082 | 0.181 |            2.050 |  86.810 |       0.250 |     0.750 |
|      8 | 0.327 |                 0.187 |                 0.467 | 0.303 |       0.405 | 0.546 | 0.086 | 0.147 |            1.600 |  79.430 |       0.350 |     0.650 |
|      9 | 0.393 |                 0.293 |                 0.493 | 0.693 |       0.148 | 0.638 | 0.122 | 0.239 |            0.370 |  94.420 |       0.150 |     0.850 |

**Scarce**

|   seed |    rf |   rescued_heavy_share |   rescued_light_share |     ear |   rsr_other |   tdi |   pss |    cr |   e1_abandonment |   steps |   exhausted |   horizon |
|-------:|------:|----------------------:|----------------------:|--------:|------------:|------:|------:|------:|-----------------:|--------:|------------:|----------:|
|      0 | 0.198 |                 0.140 |                 0.257 |   0.378 |       0.424 | 0.556 | 0.088 | 0.140 |            0.820 |  48.560 |       0.700 |     0.300 |
|      1 | 0.203 |                 0.107 |                 0.300 |   0.516 |       0.488 | 0.539 | 0.087 | 0.111 |            0.620 |  59.470 |       0.560 |     0.440 |
|      2 | 0.178 |                 0.087 |                 0.270 |   0.605 |       0.675 | 0.499 | 0.073 | 0.077 |            0.370 |  41.180 |       0.750 |     0.250 |
|      3 | 0.157 |                 0.120 |                 0.193 |   0.750 |       0.507 | 0.682 | 0.084 | 0.146 |            0.210 |  78.260 |       0.320 |     0.680 |
|      4 | 0.195 |                 0.093 |                 0.297 |   0.519 |       0.455 | 0.419 | 0.081 | 0.097 |            0.390 |  56.160 |       0.590 |     0.410 |
|      5 | 0.152 |                 0.000 |                 0.303 | nan     |       0.397 | 0.582 | 0.056 | 0.000 |            0.010 |  57.000 |       0.590 |     0.410 |
|      6 | 0.218 |                 0.120 |                 0.317 |   0.562 |       0.478 | 0.433 | 0.091 | 0.106 |            0.340 |  57.800 |       0.580 |     0.420 |
|      7 | 0.180 |                 0.083 |                 0.277 |   0.581 |       0.564 | 0.515 | 0.077 | 0.076 |            0.330 |  54.070 |       0.600 |     0.400 |
|      8 | 0.172 |                 0.057 |                 0.287 |   0.447 |       0.400 | 0.666 | 0.076 | 0.060 |            0.350 |  67.960 |       0.470 |     0.530 |
|      9 | 0.145 |                 0.020 |                 0.270 |   0.182 |       0.370 | 0.629 | 0.060 | 0.021 |            0.280 |  72.650 |       0.400 |     0.600 |

**Critical**

|   seed |    rf |   rescued_heavy_share |   rescued_light_share |     ear |   rsr_other |   tdi |   pss |    cr |   e1_abandonment |   steps |   exhausted |   horizon |
|-------:|------:|----------------------:|----------------------:|--------:|------------:|------:|------:|------:|-----------------:|--------:|------------:|----------:|
|      0 | 0.093 |                 0.007 |                 0.180 |   0.333 |       0.121 | 0.426 | 0.051 | 0.006 |            0.070 |  50.700 |       0.680 |     0.320 |
|      1 | 0.062 |                 0.010 |                 0.113 |   0.375 |       0.395 | 0.673 | 0.037 | 0.012 |            0.110 |  71.880 |       0.430 |     0.570 |
|      2 | 0.080 |                 0.000 |                 0.160 | nan     |       0.212 | 0.391 | 0.046 | 0.000 |            0.040 |  69.440 |       0.450 |     0.550 |
|      3 | 0.113 |                 0.043 |                 0.183 |   0.361 |       0.180 | 0.319 | 0.067 | 0.052 |            0.260 |  48.320 |       0.740 |     0.260 |
|      4 | 0.058 |                 0.017 |                 0.100 |   0.385 |       0.081 | 0.608 | 0.069 | 0.060 |            0.110 |  90.790 |       0.190 |     0.810 |
|      5 | 0.087 |                 0.000 |                 0.173 |   0.000 |       0.083 | 0.521 | 0.048 | 0.000 |            0.010 |  71.760 |       0.450 |     0.550 |
|      6 | 0.097 |                 0.020 |                 0.173 |   0.667 |       0.272 | 0.340 | 0.058 | 0.024 |            0.160 |  59.790 |       0.500 |     0.500 |
|      7 | 0.100 |                 0.017 |                 0.183 |   0.294 |       0.200 | 0.340 | 0.060 | 0.024 |            0.170 |  64.520 |       0.470 |     0.530 |
|      8 | 0.075 |                 0.003 |                 0.147 |   0.250 |       0.317 | 0.693 | 0.045 | 0.005 |            0.040 |  68.800 |       0.460 |     0.540 |
|      9 | 0.108 |                 0.043 |                 0.173 |   0.210 |       0.117 | 0.294 | 0.066 | 0.050 |            0.550 |  45.640 |       0.680 |     0.320 |

**Condition means ± SD over 10 seeds (main, final checkpoint):**

| level    |   rf_mean |   rf_std |   rescued_heavy_share_mean |   rescued_heavy_share_std |   ear_mean |   ear_std |   rsr_other_mean |   rsr_other_std |   tdi_mean |   tdi_std |   pss_mean |   pss_std |   cr_mean |   cr_std |   e1_abandonment_mean |   e1_abandonment_std |
|:---------|----------:|---------:|---------------------------:|--------------------------:|-----------:|----------:|-----------------:|----------------:|-----------:|----------:|-----------:|----------:|----------:|---------:|----------------------:|---------------------:|
| Abundant |     0.573 |    0.093 |                      0.422 |                     0.104 |      0.447 |     0.160 |            0.216 |           0.102 |      0.607 |     0.113 |      0.087 |     0.013 |     0.180 |    0.043 |                 3.337 |                1.349 |
| Moderate |     0.344 |    0.042 |                      0.221 |                     0.046 |      0.374 |     0.155 |            0.224 |           0.120 |      0.545 |     0.074 |      0.094 |     0.014 |     0.174 |    0.029 |                 1.693 |                0.721 |
| Scarce   |     0.180 |    0.024 |                      0.083 |                     0.045 |      0.505 |     0.159 |            0.476 |           0.091 |      0.552 |     0.090 |      0.077 |     0.012 |     0.083 |    0.047 |                 0.372 |                0.219 |
| Critical |     0.087 |    0.019 |                      0.016 |                     0.016 |      0.319 |     0.177 |            0.198 |           0.104 |      0.461 |     0.152 |      0.055 |     0.011 |     0.023 |    0.023 |                 0.152 |                0.158 |

Best-on-validation checkpoint (preregistered sensitivity), mean test RF: Abundant 0.647, Moderate 0.348, Scarce 0.181, Critical 0.093

## Baselines on the same test instances (reference)

| combo   | level    | policy      |    rf |   rescued_heavy_share |     ear |    cr |   steps |   exhausted |
|:--------|:---------|:------------|------:|----------------------:|--------:|------:|--------:|------------:|
| alt     | Abundant | cooperative | 0.975 |                 0.950 |   0.916 | 0.379 |  66.250 |       0.080 |
| alt     | Abundant | greedy      | 0.472 |                 0.000 | nan     | 0.000 |  73.750 |       0.950 |
| alt     | Abundant | random      | 0.055 |                 0.003 |   0.115 | 0.001 |  85.762 |       1.000 |
| alt     | Abundant | oracle      | 1.000 |                 1.000 |   1.000 | 0.759 |  35.040 |       0.000 |
| main    | Abundant | oracle      | 1.000 |                 1.000 |   1.000 | 0.770 |  30.070 |       0.000 |
| main    | Abundant | random      | 0.063 |                 0.003 |   0.155 | 0.001 |  62.672 |       1.000 |
| main    | Abundant | greedy      | 0.465 |                 0.000 | nan     | 0.000 |  50.080 |       0.970 |
| main    | Abundant | cooperative | 0.985 |                 0.970 |   0.907 | 0.460 |  46.680 |       0.060 |
| p0sec   | Abundant | cooperative | 0.990 |               nan     | nan     | 0.000 |  23.990 |       0.060 |
| p0sec   | Abundant | greedy      | 0.633 |               nan     | nan     | 0.000 |  29.930 |       0.970 |
| p0sec   | Abundant | random      | 0.079 |               nan     | nan     | 0.000 |  40.312 |       0.975 |
| p0sec   | Abundant | oracle      | 1.000 |               nan     | nan     | 0.000 |  23.890 |       0.000 |
| p0      | Abundant | oracle      | 1.000 |               nan     | nan     | 0.000 |  26.450 |       0.000 |
| p0      | Abundant | random      | 0.133 |               nan     | nan     | 0.000 |  62.903 |       1.000 |
| p0      | Abundant | greedy      | 0.923 |               nan     | nan     | 0.000 |  44.800 |       0.390 |
| p0      | Abundant | cooperative | 1.000 |               nan     | nan     | 0.000 |  23.840 |       0.000 |
| shifted | Abundant | cooperative | 0.873 |                 0.790 |   0.763 | 0.420 |  75.320 |       0.480 |
| shifted | Abundant | greedy      | 0.333 |                 0.000 | nan     | 0.000 |  45.600 |       1.000 |
| shifted | Abundant | random      | 0.062 |                 0.002 |   0.107 | 0.001 |  63.184 |       1.000 |
| shifted | Abundant | oracle      | 0.999 |                 0.998 |   1.000 | 0.728 |  45.350 |       0.000 |
| pooled  | Abundant | oracle      | 1.000 |                 1.000 |   1.000 | 0.770 |  30.070 |       0.000 |
| pooled  | Abundant | random      | 0.065 |                 0.003 |   0.179 | 0.001 |  59.662 |       1.000 |
| pooled  | Abundant | greedy      | 0.477 |                 0.000 | nan     | 0.000 |  53.850 |       0.930 |
| pooled  | Abundant | cooperative | 0.995 |                 0.990 |   0.905 | 0.483 |  44.350 |       0.030 |
| p0      | Moderate | cooperative | 0.907 |               nan     | nan     | 0.000 |  23.110 |       0.440 |
| p0      | Moderate | greedy      | 0.478 |               nan     | nan     | 0.000 |  23.020 |       1.000 |
| p0      | Moderate | random      | 0.055 |               nan     | nan     | 0.000 |  31.547 |       1.000 |
| p0      | Moderate | oracle      | 1.000 |               nan     | nan     | 0.000 |  19.880 |       0.000 |
| p0sec   | Moderate | oracle      | 0.915 |               nan     | nan     | 0.000 |  30.390 |       0.000 |
| p0sec   | Moderate | random      | 0.028 |               nan     | nan     | 0.000 |  20.562 |       1.000 |
| p0sec   | Moderate | greedy      | 0.295 |               nan     | nan     | 0.000 |  14.780 |       1.000 |
| p0sec   | Moderate | cooperative | 0.617 |               nan     | nan     | 0.000 |  16.400 |       0.980 |
| pooled  | Moderate | cooperative | 0.748 |                 0.610 |   0.871 | 0.374 |  32.330 |       0.930 |
| pooled  | Moderate | greedy      | 0.248 |                 0.000 | nan     | 0.000 |  24.610 |       1.000 |
| pooled  | Moderate | random      | 0.025 |                 0.001 |   0.160 | 0.001 |  29.843 |       1.000 |
| pooled  | Moderate | oracle      | 0.998 |                 0.997 |   1.000 | 0.771 |  30.660 |       0.000 |
| shifted | Moderate | oracle      | 0.733 |                 0.538 |   1.000 | 0.631 | 104.220 |       0.010 |
| shifted | Moderate | random      | 0.029 |                 0.001 |   0.088 | 0.001 |  31.819 |       1.000 |
| shifted | Moderate | greedy      | 0.177 |                 0.000 | nan     | 0.000 |  21.600 |       1.000 |
| shifted | Moderate | cooperative | 0.533 |                 0.396 |   0.753 | 0.358 |  48.920 |       1.000 |
| main    | Moderate | cooperative | 0.707 |                 0.540 |   0.827 | 0.322 |  45.070 |       0.960 |
| main    | Moderate | greedy      | 0.227 |                 0.000 | nan     | 0.000 |  23.010 |       1.000 |
| main    | Moderate | random      | 0.024 |                 0.001 |   0.111 | 0.001 |  31.497 |       1.000 |
| main    | Moderate | oracle      | 0.960 |                 0.920 |   1.000 | 0.726 |  42.390 |       0.000 |
| alt     | Moderate | oracle      | 0.997 |                 0.993 |   1.000 | 0.719 |  36.380 |       0.000 |
| alt     | Moderate | random      | 0.024 |                 0.002 |   0.176 | 0.001 |  43.703 |       1.000 |
| alt     | Moderate | greedy      | 0.252 |                 0.000 | nan     | 0.000 |  33.910 |       1.000 |
| alt     | Moderate | cooperative | 0.752 |                 0.580 |   0.731 | 0.277 |  61.320 |       0.850 |
| p0sec   | Scarce   | random      | 0.011 |               nan     | nan     | 0.000 |  11.427 |       1.000 |
| p0sec   | Scarce   | oracle      | 0.437 |               nan     | nan     | 0.000 |  43.320 |       0.120 |
| p0sec   | Scarce   | cooperative | 0.253 |               nan     | nan     | 0.000 |   8.890 |       1.000 |
| p0sec   | Scarce   | greedy      | 0.128 |               nan     | nan     | 0.000 |   7.990 |       1.000 |
| p0      | Scarce   | greedy      | 0.253 |               nan     | nan     | 0.000 |  13.300 |       1.000 |
| p0      | Scarce   | cooperative | 0.540 |               nan     | nan     | 0.000 |  14.670 |       1.000 |
| p0      | Scarce   | oracle      | 0.828 |               nan     | nan     | 0.000 |  83.830 |       0.000 |
| p0      | Scarce   | random      | 0.023 |               nan     | nan     | 0.000 |  18.558 |       1.000 |
| alt     | Scarce   | random      | 0.011 |                 0.001 |   0.111 | 0.000 |  25.840 |       1.000 |
| alt     | Scarce   | oracle      | 0.733 |                 0.493 |   1.000 | 0.576 | 144.910 |       0.000 |
| alt     | Scarce   | cooperative | 0.445 |                 0.287 |   0.768 | 0.190 |  40.180 |       1.000 |
| alt     | Scarce   | greedy      | 0.140 |                 0.000 | nan     | 0.000 |  19.300 |       1.000 |
| main    | Scarce   | greedy      | 0.123 |                 0.000 | nan     | 0.000 |  13.310 |       1.000 |
| main    | Scarce   | cooperative | 0.413 |                 0.287 |   0.789 | 0.234 |  27.160 |       1.000 |
| main    | Scarce   | oracle      | 0.617 |                 0.327 |   1.000 | 0.431 | 100.660 |       0.050 |
| main    | Scarce   | random      | 0.010 |                 0.000 |   0.083 | 0.000 |  18.538 |       1.000 |
| shifted | Scarce   | random      | 0.013 |                 0.000 |   0.000 | 0.000 |  18.883 |       1.000 |
| shifted | Scarce   | oracle      | 0.459 |                 0.212 |   1.000 | 0.384 |  97.070 |       0.090 |
| shifted | Scarce   | cooperative | 0.282 |                 0.192 |   0.604 | 0.262 |  26.640 |       1.000 |
| shifted | Scarce   | greedy      | 0.104 |                 0.000 | nan     | 0.000 |  12.360 |       1.000 |
| pooled  | Scarce   | greedy      | 0.147 |                 0.000 | nan     | 0.000 |  14.770 |       1.000 |
| pooled  | Scarce   | cooperative | 0.460 |                 0.337 |   0.842 | 0.298 |  17.640 |       1.000 |
| pooled  | Scarce   | oracle      | 0.753 |                 0.517 |   1.000 | 0.590 |  93.310 |       0.130 |
| pooled  | Scarce   | random      | 0.011 |                 0.000 |   0.083 | 0.000 |  17.695 |       1.000 |
| alt     | Critical | random      | 0.005 |                 0.000 |   0.100 | 0.000 |  16.800 |       1.000 |
| alt     | Critical | oracle      | 0.478 |                 0.283 |   1.000 | 0.395 | 139.110 |       0.080 |
| alt     | Critical | cooperative | 0.248 |                 0.177 |   0.815 | 0.151 |  24.400 |       1.000 |
| alt     | Critical | greedy      | 0.078 |                 0.000 | nan     | 0.000 |  12.200 |       1.000 |
| main    | Critical | greedy      | 0.075 |                 0.000 | nan     | 0.000 |   8.800 |       1.000 |
| main    | Critical | cooperative | 0.233 |                 0.167 |   0.704 | 0.170 |  15.210 |       1.000 |
| main    | Critical | oracle      | 0.403 |                 0.247 |   1.000 | 0.438 |  89.840 |       0.160 |
| main    | Critical | random      | 0.005 |                 0.000 |   0.000 | 0.000 |  12.448 |       1.000 |
| p0sec   | Critical | random      | 0.004 |               nan     | nan     | 0.000 |   7.294 |       1.000 |
| p0sec   | Critical | oracle      | 0.178 |               nan     | nan     | 0.000 |  46.300 |       0.040 |
| p0sec   | Critical | cooperative | 0.125 |               nan     | nan     | 0.000 |   5.560 |       1.000 |
| p0sec   | Critical | greedy      | 0.067 |               nan     | nan     | 0.000 |   5.130 |       1.000 |
| p0      | Critical | greedy      | 0.152 |               nan     | nan     | 0.000 |   8.800 |       1.000 |
| p0      | Critical | cooperative | 0.297 |               nan     | nan     | 0.000 |   9.750 |       1.000 |
| p0      | Critical | oracle      | 0.497 |               nan     | nan     | 0.000 |  96.440 |       0.090 |
| p0      | Critical | random      | 0.013 |               nan     | nan     | 0.000 |  12.455 |       1.000 |
| pooled  | Critical | random      | 0.006 |                 0.000 |   0.000 | 0.000 |  12.066 |       1.000 |
| pooled  | Critical | oracle      | 0.560 |                 0.177 |   1.000 | 0.244 |  86.230 |       0.210 |
| pooled  | Critical | cooperative | 0.277 |                 0.220 |   0.857 | 0.243 |  11.430 |       1.000 |
| pooled  | Critical | greedy      | 0.097 |                 0.000 | nan     | 0.000 |  10.240 |       1.000 |
| shifted | Critical | greedy      | 0.068 |                 0.000 | nan     | 0.000 |   8.280 |       1.000 |
| shifted | Critical | cooperative | 0.178 |                 0.116 |   0.644 | 0.219 |  14.740 |       1.000 |
| shifted | Critical | oracle      | 0.297 |                 0.160 |   1.000 | 0.439 |  95.550 |       0.100 |
| shifted | Critical | random      | 0.006 |                 0.000 |   0.000 | 0.000 |  12.725 |       1.000 |

## H0-gate (preregistered; test set, seeds 0-9, Abundant)

IQL RF per seed: 0.502, 0.595, 0.580, 0.653, 0.722, 0.405, 0.510, 0.653, 0.508, 0.598; random baseline RF 0.063. One-sided Wilcoxon signed-rank p = 0.0010; δ₁ = 1.00. **Gate PASSED** (criterion: p < 0.05 and δ₁ ≥ 0.33).

## A1 — teammate mismatch (test; mismatch score = mean of the seed's 2 mismatched teams)

| level    |   original_rf |   mismatch_rf |   difference |   seeds_original_better |
|:---------|--------------:|--------------:|-------------:|------------------------:|
| Abundant |         0.573 |         0.439 |        0.134 |                       8 |
| Moderate |         0.344 |         0.255 |        0.090 |                      10 |
| Scarce   |         0.180 |         0.137 |        0.043 |                      10 |
| Critical |         0.087 |         0.070 |        0.017 |                       8 |

## A2 — one agent replaced at test time (mean over seeds and the 3 slots)

| level    | replacement   |   iql_intact_rf |   iql_ablated_rf |   iql_intact_cr |   iql_ablated_cr |   coop_intact_rf |   coop_ablated_rf |   coop_intact_cr |   coop_ablated_cr |
|:---------|:--------------|----------------:|-----------------:|----------------:|-----------------:|-----------------:|------------------:|-----------------:|------------------:|
| Abundant | random        |           0.573 |            0.389 |           0.180 |            0.090 |            0.985 |             0.768 |            0.460 |             0.190 |
| Abundant | wait          |           0.573 |            0.292 |           0.180 |            0.103 |            0.985 |             0.810 |            0.460 |             0.309 |
| Moderate | random        |           0.344 |            0.238 |           0.174 |            0.080 |            0.707 |             0.447 |            0.322 |             0.136 |
| Moderate | wait          |           0.344 |            0.190 |           0.174 |            0.101 |            0.707 |             0.475 |            0.322 |             0.208 |
| Scarce   | random        |           0.180 |            0.122 |           0.083 |            0.034 |            0.413 |             0.244 |            0.234 |             0.107 |
| Scarce   | wait          |           0.180 |            0.095 |           0.083 |            0.039 |            0.413 |             0.233 |            0.234 |             0.152 |
| Critical | random        |           0.087 |            0.066 |           0.023 |            0.009 |            0.233 |             0.134 |            0.170 |             0.081 |
| Critical | wait          |           0.087 |            0.049 |           0.023 |            0.011 |            0.233 |             0.103 |            0.170 |             0.116 |

## A3 primary — p_heavy = 0 world, main budgets (test, mean over seeds; seed-level rows in seed_level_learned.csv)

| level    |    rf |   rescued_heavy_share |    cr |   tdi |   rsr_other |   steps |   exhausted |   horizon |
|:---------|------:|----------------------:|------:|------:|------------:|--------:|------------:|----------:|
| Abundant | 0.931 |                   nan | 0.000 | 0.590 |       0.264 |  56.115 |       0.053 |     0.224 |
| Moderate | 0.639 |                   nan | 0.000 | 0.557 |       0.301 |  61.137 |       0.494 |     0.412 |
| Scarce   | 0.339 |                   nan | 0.000 | 0.494 |       0.473 |  45.226 |       0.707 |     0.293 |
| Critical | 0.198 |                   nan | 0.000 | 0.314 |       0.149 |  39.102 |       0.755 |     0.245 |

## A3 secondary — p_heavy = 0 world, its own calibration (test, mean over seeds; seed-level rows in seed_level_learned.csv)

| level    |    rf |   rescued_heavy_share |    cr |   tdi |   rsr_other |   steps |   exhausted |   horizon |
|:---------|------:|----------------------:|------:|------:|------------:|--------:|------------:|----------:|
| Abundant | 0.777 |                   nan | 0.000 | 0.556 |       0.226 |  41.334 |       0.261 |     0.458 |
| Moderate | 0.379 |                   nan | 0.000 | 0.546 |       0.370 |  33.881 |       0.568 |     0.431 |
| Scarce   | 0.144 |                   nan | 0.000 | 0.573 |       0.560 |  29.060 |       0.526 |     0.474 |
| Critical | 0.084 |                   nan | 0.000 | 0.454 |       0.150 |  26.004 |       0.571 |     0.429 |

## A4 — solo-trained agents deployed together (test, mean over seeds; seed-level rows in seed_level_learned.csv)

| level    |    rf |   rescued_heavy_share |    cr |   tdi |   rsr_other |   steps |   exhausted |   horizon |
|:---------|------:|----------------------:|------:|------:|------------:|--------:|------------:|----------:|
| Abundant | 0.101 |                 0.007 | 0.002 | 0.655 |       0.870 |  75.699 |       0.700 |     0.300 |
| Moderate | 0.039 |                 0.000 | 0.000 | 0.662 |       0.853 |  33.617 |       0.970 |     0.030 |
| Scarce   | 0.015 |                 0.000 | 0.000 | 0.672 |       0.822 |  18.883 |       0.999 |     0.001 |
| Critical | 0.006 |                 0.000 | 0.000 | 0.695 |       0.776 |  12.418 |       0.999 |     0.001 |

## A6 — equal environment steps (vs main, equal episodes) (test, mean over seeds; seed-level rows in seed_level_learned.csv)

| level    |    rf |   rescued_heavy_share |    cr |   tdi |   rsr_other |   steps |   exhausted |   horizon |
|:---------|------:|----------------------:|------:|------:|------------:|--------:|------------:|----------:|
| Moderate | 0.422 |                 0.307 | 0.208 | 0.521 |       0.364 |  58.001 |       0.625 |     0.374 |
| Scarce   | 0.145 |                 0.054 | 0.052 | 0.536 |       0.533 |  61.591 |       0.519 |     0.481 |
| Critical | 0.104 |                 0.056 | 0.072 | 0.439 |       0.239 |  54.595 |       0.580 |     0.420 |

## Ablation — pooled team budget (test, mean over seeds; seed-level rows in seed_level_learned.csv)

| level    |    rf |   rescued_heavy_share |    cr |   tdi |   rsr_other |   steps |   exhausted |   horizon |
|:---------|------:|----------------------:|------:|------:|------------:|--------:|------------:|----------:|
| Abundant | 0.667 |                 0.552 | 0.213 | 0.519 |       0.288 |  93.344 |       0.046 |     0.780 |
| Moderate | 0.405 |                 0.295 | 0.207 | 0.537 |       0.316 |  84.794 |       0.459 |     0.538 |
| Scarce   | 0.195 |                 0.100 | 0.092 | 0.589 |       0.323 |  58.808 |       0.944 |     0.056 |
| Critical | 0.129 |                 0.043 | 0.053 | 0.475 |       0.178 |  49.492 |       0.999 |     0.001 |

## Alternate configuration L12_d04 (test, mean over seeds; seed-level rows in seed_level_learned.csv)

| level    |    rf |   rescued_heavy_share |    cr |   tdi |   rsr_other |   steps |   exhausted |   horizon |
|:---------|------:|----------------------:|------:|------:|------------:|--------:|------------:|----------:|
| Abundant | 0.455 |                 0.346 | 0.140 | 0.626 |       0.217 | 148.575 |       0.002 |     0.985 |
| Moderate | 0.372 |                 0.260 | 0.156 | 0.540 |       0.198 | 104.430 |       0.428 |     0.572 |
| Scarce   | 0.198 |                 0.107 | 0.090 | 0.569 |       0.430 |  84.400 |       0.553 |     0.447 |
| Critical | 0.068 |                 0.013 | 0.014 | 0.635 |       0.222 | 107.279 |       0.358 |     0.642 |

## A3 — difference-in-differences per seed (RF, Abundant minus Critical; primary)

|   seed |   drop_p05 |   drop_p0 |    DiD |
|-------:|-----------:|----------:|-------:|
|      0 |      0.408 |     0.755 | -0.347 |
|      1 |      0.533 |     0.628 | -0.095 |
|      2 |      0.500 |     0.688 | -0.188 |
|      3 |      0.540 |     0.747 | -0.207 |
|      4 |      0.663 |     0.703 | -0.040 |
|      5 |      0.318 |     0.742 | -0.423 |
|      6 |      0.413 |     0.763 | -0.350 |
|      7 |      0.553 |     0.758 | -0.205 |
|      8 |      0.433 |     0.827 | -0.393 |
|      9 |      0.490 |     0.722 | -0.232 |

Mean DiD = -0.248 (seeds with DiD > 0: 0/10). Test and CI: Phase 6.

## Exp5 — generalization: same-distribution test vs shifted test (wall 0.25, density 0.09)

| level    |   shifted_rf |   test_rf |
|:---------|-------------:|----------:|
| Abundant |        0.429 |     0.573 |
| Moderate |        0.256 |     0.344 |
| Scarce   |        0.139 |     0.180 |
| Critical |        0.079 |     0.087 |

## Exp5 — cross-ρ transfer matrix (rows: trained at; columns: tested at; mean RF over seeds)

| train_level   |   Abundant |   Moderate |   Scarce |   Critical |
|:--------------|-----------:|-----------:|---------:|-----------:|
| Abundant      |      0.573 |      0.192 |    0.072 |      0.010 |
| Moderate      |      0.161 |      0.344 |    0.207 |      0.116 |
| Scarce        |      0.059 |      0.169 |    0.180 |      0.121 |
| Critical      |      0.049 |      0.106 |    0.100 |      0.087 |
