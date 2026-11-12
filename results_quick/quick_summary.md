# Quick pipeline check (NOT study results)

Scale: 3 seeds x 3000 episodes per level, 200 training maps, 30 test maps. Full study: 10 seeds x 8,000 episodes, 1,000 / 100 maps (results/).

| level | IQL RF (mean) | random | greedy | cooperative | oracle reference |
|---|---|---|---|---|---|
| Abundant | 0.243 | 0.067 | 0.450 | 0.983 | 1.000 |
| Moderate | 0.106 | 0.037 | 0.217 | 0.756 | 0.967 |
| Scarce | 0.048 | 0.013 | 0.117 | 0.389 | 0.594 |
| Critical | 0.033 | 0.006 | 0.072 | 0.239 | 0.394 |

H0-gate (quick, one-sided, 3 seeds): p = 0.1250 (with 3 seeds the smallest possible p is 0.125, so the quick run cannot pass the preregistered gate; it only checks that the code path works).
Friedman (quick): chi2 = 8.79, p = 0.0322, W = 0.98; Page two-sided p = 0.0014.

Total time: 174.4 s

## Log

[  27.3 s] 1 tests: 264 passed, 1 warning in 26.73s
[ 172.1 s] 2 trained and evaluated 12 IQL runs (3000 episodes each)
[ 173.9 s] 3 baselines and oracle reference evaluated
[ 174.4 s] 4 statistics and figure written
