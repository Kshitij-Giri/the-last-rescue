"""Independent verification of the experiment results and statistics. Exits non-zero on ANY mismatch.

Checks
  V1 seed-level values: recomputed from the raw episode CSVs (results/eval) with an independent pandas implementation and
     compared with results/stats/seed_level_learned.csv and baselines_test.csv (tolerance 1e-12).
  V2 condition means: recomputed from V1 values and compared with results/stats/condition_means.csv.
  V3 confirmatory tests: recomputed directly with scipy (not tlr.stats) plus an independent Holm implementation;
     compared with h1_h2_omnibus.csv, h1_h2_pairwise.csv, h3_vs_baselines.csv, h4_A1_mismatch.csv, h6_A4_solo.csv, and
     results.json (H0, H5).
  V4 reproducibility: scripts/run_stats.py is re-run into a scratch directory; every output file must be byte-identical
     or, where floating-point summation order differs between platforms, numerically equal (relative tolerance 1e-5).
  V5 claims ledger: every entry of docs/claims.yaml is checked against its source; docs/claims_ledger.md is written.
  V6 provenance: training-run count and the manifest hashes of raw evaluation files.
Usage: python scripts/verify_results.py      (log: results/logs/verify_results.txt)
"""

from __future__ import annotations

import filecmp
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from scipy import stats as ss

ROOT = Path(__file__).resolve().parents[1]
ST = ROOT / "results" / "stats"
LEVELS = ["Abundant", "Moderate", "Scarce", "Critical"]
FAIL: list[str] = []
LOG: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    LOG.append(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" - {detail}" if detail else ""))
    if not ok:
        FAIL.append(name)


def seed_values(df: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    """Independent re-implementation of the preregistered seed-level values."""
    g = df.groupby(keys, sort=False)
    out = pd.DataFrame({
        "rf": g.rf.mean(),
        "rescued_heavy_share": g.rescued_heavy.sum() / g.n_heavy.sum().replace(0, np.nan),
        "ear": g.ear_num.sum() / g.ear_den.sum().replace(0, np.nan),
        "rsr": (g.rsr_other_num.sum() + g.rsr_self_num.sum()) / g.rsr_den.sum().replace(0, np.nan),
        "rsr_other": g.rsr_other_num.sum() / g.rsr_den.sum().replace(0, np.nan),
        "tdi": g.tdi.mean(), "pss": g.pss_num.sum() / g.pss_den.sum().replace(0, np.nan),
        "gini_consumption": g.gini_consumption.mean(), "cr": g.cr_num.sum() / g.cr_den.sum().replace(0, np.nan),
        "steps": g.steps.mean()})
    return out.reset_index()


def holm(p):
    p = np.asarray(p, float)
    order = np.argsort(p)
    adj = np.empty_like(p)
    m, run = len(p), 0.0
    for i, j in enumerate(order):
        run = max(run, min(1.0, (m - i) * p[j]))
        adj[j] = run
    return adj


def snap(d):
    """Independent floating-point tie handling (same principle as tlr.stats.ZERO_TOL; see deviations C6)."""
    d = np.asarray(d, float)
    return np.where(np.abs(d) < 1e-9, 0.0, d)


def close(a, b, tol=1e-12) -> bool:
    a, b = np.asarray(a, float), np.asarray(b, float)
    return a.shape == b.shape and bool(np.all((np.isnan(a) & np.isnan(b)) | (np.abs(a - b) <= tol)))


def _leaves(x, path=""):
    if isinstance(x, dict):
        for k, v in x.items():
            yield from _leaves(v, f"{path}.{k}")
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from _leaves(v, f"{path}[{i}]")
    else:
        yield path, x


def _same_value(a, b) -> bool:
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        return bool(np.isclose(a, b, rtol=1e-5, atol=1e-12, equal_nan=True))
    return a == b


def numerically_equal(f1: Path, f2: Path) -> bool:
    """Same structure and text; numbers equal within a relative tolerance of 1e-5."""
    if not f2.exists():
        return False
    if f1.suffix == ".json":
        a, b = list(_leaves(json.loads(f1.read_text()))), list(_leaves(json.loads(f2.read_text())))
        return len(a) == len(b) and all(pa == pb and _same_value(va, vb) for (pa, va), (pb, vb) in zip(a, b))
    a, b = pd.read_csv(f1), pd.read_csv(f2)
    if list(a.columns) != list(b.columns) or a.shape != b.shape:
        return False
    for c in a.columns:
        if pd.api.types.is_numeric_dtype(a[c]) and pd.api.types.is_numeric_dtype(b[c]):
            if not np.allclose(a[c].astype(float), b[c].astype(float), rtol=1e-5, atol=1e-12, equal_nan=True):
                return False
        elif not a[c].fillna("").astype(str).equals(b[c].fillna("").astype(str)):
            return False
    return True


def main() -> None:
    raw = pd.concat([pd.read_csv(f) for f in sorted((ROOT / "results" / "eval" / "learned").glob("*.csv"))])
    mine = seed_values(raw, ["block", "level", "checkpoint", "seed"])
    theirs = pd.read_csv(ST / "seed_level_learned.csv")
    j = mine.merge(theirs, on=["block", "level", "checkpoint", "seed"], suffixes=("_v", "_s"))
    check("V1 seed-level rows matched", len(j) == len(theirs) == len(mine), f"{len(j)} rows")
    for c in ("rf", "rescued_heavy_share", "ear", "rsr", "rsr_other", "tdi", "pss", "gini_consumption", "cr", "steps"):
        check(f"V1 seed-level {c}", close(j[f"{c}_v"], j[f"{c}_s"]))
    braw = pd.concat([pd.read_csv(f) for f in sorted((ROOT / "results" / "eval" / "baselines").glob("*.csv"))])
    bm = seed_values(braw, ["combo", "level", "policy"]).merge(pd.read_csv(ST / "baselines_test.csv"),
                                                               on=["combo", "level", "policy"], suffixes=("_v", "_s"))
    check("V1 baseline rows", len(bm) == 96, f"{len(bm)} rows")
    for c in ("rf", "cr", "rescued_heavy_share"):
        check(f"V1 baselines {c}", close(bm[f"{c}_v"], bm[f"{c}_s"]))

    CM = pd.read_csv(ST / "condition_means.csv")
    for (block, ckpt, level), g in mine.groupby(["block", "checkpoint", "level"]):
        for m in ("rf", "cr", "ear", "tdi", "pss"):
            ref = CM[(CM.block == block) & (CM.checkpoint == ckpt) & (CM.level == level) & (CM.metric == m)]["mean"]
            check(f"V2 mean {block}/{ckpt}/{level}/{m}", close(np.nanmean(g[m]), ref.iloc[0]))

    def M(metric, block="main"):
        d = mine[(mine.block == block) & (mine.checkpoint == "final")].set_index(["seed", "level"])[metric]
        return np.array([[d[(s, l)] for l in LEVELS] for s in range(10)])

    OM = pd.read_csv(ST / "h1_h2_omnibus.csv").set_index("metric")
    h2p = []
    for m in ("rf", "ear", "rsr", "rsr_other", "tdi", "pss", "gini_consumption", "cr"):
        X = M(m)
        X = X[~np.isnan(X).any(axis=1)]
        fr = ss.friedmanchisquare(*X.T)
        check(f"V3 Friedman {m}", close(fr.statistic, OM.loc[m, "friedman_chi2"], 1e-9) and
              close(fr.pvalue, OM.loc[m, "friedman_p"], 1e-12) and int(OM.loc[m, "n_complete"]) == len(X))
        dec = ss.page_trend_test(X, predicted_ranks=[4, 3, 2, 1]).pvalue
        inc = ss.page_trend_test(X, predicted_ranks=[1, 2, 3, 4]).pvalue
        check(f"V3 Page {m}", close(min(1, 2 * min(dec, inc)), OM.loc[m, "page_p_two_sided"], 1e-12))
        if m != "rf":
            h2p.append(fr.pvalue)
    check("V3 Holm H2 Friedman", close(holm(h2p), OM.loc[["ear", "rsr", "rsr_other", "tdi", "pss", "gini_consumption",
                                                           "cr"], "friedman_p_holm"].values, 1e-12))
    PW = pd.read_csv(ST / "h1_h2_pairwise.csv")
    rf = M("rf")
    pv = []
    for a in range(4):
        for b in range(a + 1, 4):
            pv.append(ss.wilcoxon(snap(rf[:, a] - rf[:, b]), zero_method="wilcox", correction=True).pvalue)
    ref = PW[PW.metric == "rf"]
    check("V3 RF pairwise p", close(pv, ref.p.values, 1e-12) and close(holm(pv), ref.p_holm6.values, 1e-12))
    sb = pd.read_csv(ST / "baselines_test.csv").set_index(["combo", "level", "policy"])
    H3 = pd.read_csv(ST / "h3_vs_baselines.csv")
    p3 = [ss.wilcoxon(snap(rf[:, LEVELS.index(r.level)] - sb.loc[("main", r.level, r.baseline), "rf"]),
                      zero_method="wilcox", correction=True).pvalue for r in H3.itertuples()]
    check("V3 H3 p and Holm(12)", close(p3, H3.p.values, 1e-12) and close(holm(p3), H3.p_holm12.values, 1e-12))
    r = json.loads((ST / "results.json").read_text())
    h0 = ss.wilcoxon(snap(rf[:, 0] - sb.loc[("main", "Abundant", "random"), "rf"]), alternative="greater",
                     zero_method="wilcox", correction=True)
    check("V3 H0", close(h0.pvalue, r["H0"]["p"], 1e-12) and r["H0"]["passed"])
    a1 = pd.concat([pd.read_csv(f) for f in sorted((ROOT / "results" / "eval" / "A1").glob("*.csv"))])
    a1s = seed_values(a1, ["level", "round", "seed"]).groupby(["level", "seed"]).rf.mean()
    H4 = pd.read_csv(ST / "h4_A1_mismatch.csv").set_index("level")
    p4 = []
    for j_, level in enumerate(LEVELS):
        d = snap(rf[:, j_] - np.array([a1s[(level, s)] for s in range(10)]))
        p4.append(ss.wilcoxon(d, zero_method="wilcox", correction=True).pvalue)
        check(f"V3 H4 diff {level}", close(d.mean(), H4.loc[level, "mean_diff"], 1e-9))
    check("V3 H4 p and Holm(4)", close(p4, H4.loc[LEVELS, "p"].values, 1e-12) and
          close(holm(p4), H4.loc[LEVELS, "p_holm4"].values, 1e-12))
    solo = M("rf", "solo")
    H6 = pd.read_csv(ST / "h6_A4_solo.csv").set_index("level")
    p6 = [ss.wilcoxon(snap(rf[:, k] - solo[:, k]), zero_method="wilcox", correction=True).pvalue for k in range(4)]
    check("V3 H6 p and Holm(4)", close(p6, H6.loc[LEVELS, "p"].values, 1e-12) and
          close(holm(p6), H6.loc[LEVELS, "p_holm4"].values, 1e-12))
    p0 = M("rf", "p0")
    did = (rf[:, 0] - rf[:, 3]) - (p0[:, 0] - p0[:, 3])
    check("V3 H5 DiD and p", close(did, r["H5"]["did_per_seed"], 1e-12) and
          close(ss.wilcoxon(snap(did), zero_method="wilcox", correction=True).pvalue, r["H5"]["p"], 1e-12))

    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run([sys.executable, str(ROOT / "scripts" / "run_stats.py"), "--out", tmp], check=True,
                       capture_output=True)
        names = sorted(p.name for p in ST.glob("*") if p.suffix in (".csv", ".json"))
        same = [n for n in names if filecmp.cmp(ST / n, Path(tmp) / n, shallow=False)]
        equal = [n for n in names if n in same or numerically_equal(ST / n, Path(tmp) / n)]
        check("V4 run_stats.py reproduces every output", len(equal) == len(names),
              f"{len(same)}/{len(names)} byte-identical, {len(equal)}/{len(names)} numerically equal")

    claims = yaml.safe_load((ROOT / "docs" / "claims.yaml").read_text())
    rows = []
    for c in claims:
        try:
            if c["kind"] == "json":
                v = json.loads((ROOT / c["file"]).read_text())
                for k in c["path"].split("."):
                    v = v[k]
            elif c["kind"] == "yaml":
                v = yaml.safe_load((ROOT / c["file"]).read_text())
                for k in c["path"].split("."):
                    v = v[k]
            elif c["kind"] == "csv":
                d = pd.read_csv(ROOT / c["file"])
                for k, val in c["where"].items():
                    d = d[d[k].astype(str) == str(val)]
                assert len(d) == 1, f"{len(d)} rows match"
                v = d[c["column"]].iloc[0]
            elif c["kind"] == "runs":
                v = len(list((ROOT / "results" / "runs").glob("**/run.json")))
            ok = abs(float(v) - float(c["value"])) <= float(c["tol"])
        except Exception as e:  # noqa: BLE001
            v, ok = f"ERROR {e}", False
        check(f"V5 claim {c['id']}", ok, f"stated {c['value']}, source {v}")
        rows.append({"id": c["id"], "family": c["family"], "claim": c["claim"], "source": c.get("file", "results/runs"),
                     "locator": c.get("path") or c.get("where") or c.get("query"), "stated": c["value"],
                     "source_value": v, "verified": "yes" if ok else "NO"})
    L = pd.DataFrame(rows)
    (ROOT / "docs" / "claims_ledger.md").write_text(
        "# Claims ledger (generated by scripts/verify_results.py from docs/claims.yaml)\n\n"
        "Every key number in the result summaries maps to the file and locator below; `verified` = the stated value "
        "matches the source within the stated rounding.\n\n" + L.to_markdown(index=False) + "\n")

    n_runs = len(list((ROOT / "results" / "runs").glob("**/run.json")))
    check("V6 training runs", n_runs == 350, f"{n_runs}")
    man = json.loads((ROOT / "results" / "phase5" / "phase5_manifest.json").read_text())["files"]
    evals = {k: v for k, v in man.items() if k.startswith("results/eval/")}
    bad = [k for k, h in evals.items() if hashlib.sha256((ROOT / k).read_bytes()).hexdigest() != h]
    check("V6 raw evaluation CSVs unchanged since the experiment manifest", not bad, f"{len(evals) - len(bad)}/{len(evals)}")

    LOG.append(f"\n{len(LOG) - len(FAIL)} checks passed, {len(FAIL)} failed")
    text = "\n".join(LOG)
    (ROOT / "results" / "logs" / "verify_results.txt").write_text(text + "\n")
    print(text)
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
