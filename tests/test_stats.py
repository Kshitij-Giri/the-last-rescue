"""Statistical helpers (D26): known-answer checks against hand computation and scipy."""

import math

import numpy as np
import pytest
from scipy import stats as ss

from tlr.stats import (bootstrap_ci, cliffs_delta, friedman, holm, one_sample_vs_constant, page_two_sided,
                       paired_bootstrap_ci, vif, wilcoxon_test)


def test_holm_by_hand():
    # p = [0.01, 0.04, 0.03, 0.20] -> sorted 0.01, 0.03, 0.04, 0.20 -> x4, x3, x2, x1 = 0.04, 0.09, 0.08->0.09, 0.20
    assert holm([0.01, 0.04, 0.03, 0.20]) == pytest.approx([0.04, 0.09, 0.09, 0.20])
    assert holm([0.5, math.nan, 0.01]) [1] != holm([0.5, math.nan, 0.01])[1]   # NaN stays NaN
    assert holm([0.6, 0.6]) == [1.0, 1.0]


def test_wilcoxon_exact_all_positive():
    d = np.arange(1, 11) / 100.0                         # 10 distinct positive differences
    r = wilcoxon_test(d, "greater")
    assert r["method"] == "exact" and r["p"] == pytest.approx(1 / 1024) and r["r_rb"] == 1.0
    r2 = wilcoxon_test(d)
    assert r2["p"] == pytest.approx(2 / 1024)


def test_rank_biserial_by_hand():
    d = np.array([1.0, 2.0, -3.0, 4.0])                  # ranks 1,2,3,4; W+ = 7, W- = 3 -> r = 0.4
    assert wilcoxon_test(d)["r_rb"] == pytest.approx(0.4)


def test_one_sample_delta():
    r = one_sample_vs_constant([0.5, 0.6, 0.1, 0.7], 0.3)
    assert r["delta_1"] == pytest.approx((3 - 1) / 4) and r["n_above"] == 3


def test_friedman_matches_scipy_and_kendall_w():
    rng = np.random.default_rng(0)
    M = rng.normal(size=(10, 4)) + np.array([3, 2, 1, 0])
    r = friedman(M)
    ref = ss.friedmanchisquare(*M.T)
    assert r["chi2"] == pytest.approx(ref.statistic) and r["p"] == pytest.approx(ref.pvalue)
    assert r["kendall_w"] == pytest.approx(ref.statistic / (10 * 3))
    M2 = M.copy()
    M2[2, 1] = np.nan
    assert friedman(M2)["n"] == 9                       # complete-block rule


def test_page_direction():
    M = np.tile([4.0, 3.0, 2.0, 1.0], (8, 1)) + np.random.default_rng(1).normal(scale=0.01, size=(8, 4))
    r = page_two_sided(M)
    assert r["direction"] == "decreasing" and r["p"] < 0.001


def test_bootstrap_reproducible_and_paired():
    x = [0.1, 0.4, 0.35, 0.8, 0.5]
    assert bootstrap_ci(x, "a") == bootstrap_ci(x, "a")
    lo, hi = bootstrap_ci(x, "a")
    assert lo <= np.mean(x) <= hi
    a, b = [1.0, 2.0, 3.0], [0.5, 1.5, 2.5]
    assert paired_bootstrap_ci(a, b, "p") == pytest.approx((0.5, 0.5))   # constant paired difference


def test_cliffs_delta():
    assert cliffs_delta([3, 4], [1, 2]) == 1.0 and cliffs_delta([1, 2], [1, 2]) == 0.0


def test_vif_independent_columns_near_one():
    Z = np.random.default_rng(3).normal(size=(200, 3))
    assert all(v < 1.2 for v in vif(Z))


def test_floating_point_ties_are_zero():
    """C6: 45/600 computed two ways differs by ~1e-17; it must count as an exact zero and be dropped."""
    a = np.mean(np.array([45 / 6] * 1 + [0.0] * 99) / 100 * 6 / 6)   # arbitrary float path
    d = np.array([0.1, 0.2, -0.05, 0.3, 1e-17, -2e-17])
    r = wilcoxon_test(d)
    assert r["n_nonzero"] == 4
    assert one_sample_vs_constant([0.075 + 1e-17, 0.2, 0.3], 0.075)["n_above"] == 2
