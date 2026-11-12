"""Statistical procedures of preregistration v1.0 §5 (as fixed in design_decisions D26).

All functions are pure and deterministic. Bootstrap generators are seeded from the CRC32 of a label so every interval is
reproducible regardless of the order in which quantities are computed. The unit of analysis is the training seed.
"""

from __future__ import annotations

import math
import zlib
from typing import Sequence

import numpy as np
from scipy import stats as ss

N_BOOT = 10_000
# Differences smaller than this are exact ties computed through floating-point means (e.g. 45/600 vs 45/600 giving
# +-1e-17). Rescue fractions move in steps of 1/600 here, so no real difference is this small. Snapping them to 0 makes
# Wilcoxon's zero handling (zero_method="wilcox", preregistered) independent of rounding noise (deviations C6).
ZERO_TOL = 1e-9


def _rng(label: str) -> np.random.Generator:
    return np.random.default_rng(np.random.SeedSequence(zlib.crc32(label.encode("utf-8"))))


def bootstrap_ci(x: Sequence[float], label: str, level: float = 0.95, n_boot: int = N_BOOT) -> tuple[float, float]:
    """Percentile CI of the mean, resampling seeds."""
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    if len(x) == 0:
        return (math.nan, math.nan)
    idx = _rng(label).integers(0, len(x), size=(n_boot, len(x)))
    means = x[idx].mean(axis=1)
    a = (1 - level) / 2
    return (float(np.quantile(means, a)), float(np.quantile(means, 1 - a)))


def paired_bootstrap_ci(a: Sequence[float], b: Sequence[float], label: str, level: float = 0.95,
                        n_boot: int = N_BOOT) -> tuple[float, float]:
    """Percentile CI of mean(a - b), resampling seeds jointly (each seed keeps both of its values)."""
    d = np.asarray(a, dtype=float) - np.asarray(b, dtype=float)
    return bootstrap_ci(d, label, level, n_boot)


def wilcoxon_test(d: Sequence[float], alternative: str = "two-sided") -> dict[str, float]:
    """Wilcoxon signed-rank on differences d (zeros dropped), with matched-pairs rank-biserial r."""
    d = np.asarray(d, dtype=float)
    d = d[~np.isnan(d)]
    d = np.where(np.abs(d) < ZERO_TOL, 0.0, d)
    nz = d[d != 0]
    out = {"n": int(len(d)), "n_nonzero": int(len(nz)), "median_diff": float(np.median(d)) if len(d) else math.nan,
           "mean_diff": float(np.mean(d)) if len(d) else math.nan}
    if len(nz) == 0:
        return {**out, "statistic": math.nan, "p": 1.0, "r_rb": 0.0, "method": "all-zero"}
    res = ss.wilcoxon(d, zero_method="wilcox", correction=True, alternative=alternative, method="auto")
    ranks = ss.rankdata(np.abs(nz))
    wp, wm = float(ranks[nz > 0].sum()), float(ranks[nz < 0].sum())
    ties = len(np.unique(np.abs(nz))) < len(nz)
    method = "exact" if (len(nz) <= 50 and not ties and len(nz) == len(d)) else "approx"
    return {**out, "statistic": float(res.statistic), "p": float(res.pvalue), "r_rb": (wp - wm) / (wp + wm),
            "W_plus": wp, "W_minus": wm, "method": method}


def one_sample_vs_constant(x: Sequence[float], c: float, alternative: str = "two-sided") -> dict[str, float]:
    """H0/H3: seed values vs a fixed baseline value; adds delta_1 = (#above - #below) / n."""
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    d = x - c
    d = np.where(np.abs(d) < ZERO_TOL, 0.0, d)
    out = wilcoxon_test(d, alternative)
    out["delta_1"] = float(((d > 0).sum() - (d < 0).sum()) / len(d)) if len(d) else math.nan
    out["n_above"], out["n_below"] = int((d > 0).sum()), int((d < 0).sum())
    return out


def complete_blocks(M: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Rows (seeds) with no NaN in any column (preregistration §5.1 complete-block rule); returns (matrix, row mask)."""
    keep = ~np.isnan(M).any(axis=1)
    return M[keep], keep


def friedman(M: np.ndarray) -> dict[str, float]:
    """Friedman test over complete blocks (rows = seeds, columns = conditions) + Kendall's W."""
    X, keep = complete_blocks(np.asarray(M, dtype=float))
    n, k = X.shape
    if n < 2:
        return {"n": n, "chi2": math.nan, "p": math.nan, "kendall_w": math.nan}
    res = ss.friedmanchisquare(*[X[:, j] for j in range(k)])
    chi2 = float(res.statistic)
    return {"n": n, "chi2": chi2, "p": float(res.pvalue), "kendall_w": chi2 / (n * (k - 1))}


def page_two_sided(M: np.ndarray) -> dict[str, float]:
    """Page's L for an ordered trend across columns, tested in both directions; two-sided p = min(1, 2 min(p))."""
    X, _ = complete_blocks(np.asarray(M, dtype=float))
    n, k = X.shape
    if n < 2:
        return {"n": n, "L_dec": math.nan, "p_dec": math.nan, "p_inc": math.nan, "p": math.nan, "direction": ""}
    # columns are ordered Abundant .. Critical. "decreasing" = values fall from Abundant to Critical.
    dec = ss.page_trend_test(X, predicted_ranks=list(range(k, 0, -1)))
    inc = ss.page_trend_test(X, predicted_ranks=list(range(1, k + 1)))
    p = min(1.0, 2 * min(float(dec.pvalue), float(inc.pvalue)))
    return {"n": n, "L_dec": float(dec.statistic), "p_dec": float(dec.pvalue), "L_inc": float(inc.statistic),
            "p_inc": float(inc.pvalue), "p": p, "direction": "decreasing" if dec.pvalue < inc.pvalue else "increasing"}


def holm(pvals: Sequence[float]) -> list[float]:
    """Holm step-down adjusted p-values (NaN entries are left NaN and not counted)."""
    p = np.asarray(pvals, dtype=float)
    ok = ~np.isnan(p)
    m = int(ok.sum())
    adj = np.full_like(p, np.nan)
    if m == 0:
        return adj.tolist()
    idx = np.flatnonzero(ok)[np.argsort(p[ok], kind="stable")]
    running = 0.0
    for i, j in enumerate(idx):
        running = max(running, min(1.0, (m - i) * p[j]))
        adj[j] = running
    return adj.tolist()


def kruskal(groups: Sequence[Sequence[float]]) -> dict[str, float]:
    g = [np.asarray(x, dtype=float)[~np.isnan(np.asarray(x, dtype=float))] for x in groups]
    res = ss.kruskal(*g)
    return {"H": float(res.statistic), "p": float(res.pvalue)}


def cliffs_delta(x: Sequence[float], y: Sequence[float]) -> float:
    """(#x > y - #x < y) / (n m), unpaired."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    x, y = x[~np.isnan(x)], y[~np.isnan(y)]
    if len(x) == 0 or len(y) == 0:
        return math.nan
    diff = x[:, None] - y[None, :]
    return float(((diff > 0).sum() - (diff < 0).sum()) / diff.size)


def ols(y: np.ndarray, X: np.ndarray) -> np.ndarray:
    """Least-squares coefficients (X must include an intercept column)."""
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return beta


def vif(Z: np.ndarray) -> list[float]:
    """Variance inflation factor of each column of Z (regressed on the others plus an intercept)."""
    out = []
    for j in range(Z.shape[1]):
        others = np.delete(Z, j, axis=1)
        Xo = np.column_stack([np.ones(len(Z)), others])
        b = ols(Z[:, j], Xo)
        resid = Z[:, j] - Xo @ b
        r2 = 1 - resid.var() / Z[:, j].var() if Z[:, j].var() > 0 else 0.0
        out.append(float(1 / (1 - r2)) if r2 < 1 else math.inf)
    return out
