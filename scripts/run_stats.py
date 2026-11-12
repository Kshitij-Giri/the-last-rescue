"""Phase 6 statistical analysis (preregistration v1.0 §5; design_decisions D26). Reads ONLY raw episode CSVs in
results/eval/; writes results/stats/*.csv, *.json and stats_summary.md.

Families:
  CONFIRMATORY  H0 gate; H1 (RF across rho: Friedman, Page, 6 pairwise Wilcoxon, Holm); H2 (7 cooperation metrics:
                Friedman and Page, Holm across 7; pairwise Holm across 6 within metric); H3 (IQL vs random/greedy/
                cooperative at each rho, Holm across 12); H4 (A1 original vs mismatched, Holm across 4); H5 (A3 DiD);
                H6 (A4 joint vs solo, Holm across 4).
  SECONDARY     Kruskal-Wallis + Cliff's delta (unpaired); A3 secondary (a) own-calibration world, (b) oracle-normalised
                DiD + 4-level interaction curves (estimates and CIs, not tested); best-validation and stable-run
                sensitivities of H1.
  EXPLORATORY   A2, A5 diagnostics, A6, pooled, alternate configuration, p_heavy = 0 trend, shifted test, transfer matrix,
                Exp4 (E1, E2, E3, individual vs collective), A8 mediation (association only). Unadjusted p-values.
Usage: python scripts/run_stats.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as ss

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tlr.experiments import LEVELS, SEEDS, run_dir  # noqa: E402
from tlr.metrics import e3_conflict_flags  # noqa: E402
from tlr.stats import (N_BOOT, bootstrap_ci, cliffs_delta, friedman, holm, kruskal, ols,  # noqa: E402
                       one_sample_vs_constant, page_two_sided, paired_bootstrap_ci, vif, wilcoxon_test)
from tlr.train import summarize_eval  # noqa: E402

EVAL = ROOT / "results" / "eval"
OUT = ROOT / "results" / "stats"
H2_METRICS = ["ear", "rsr", "rsr_other", "tdi", "pss", "gini_consumption", "cr"]
REPORT_METRICS = ["rf", "rescued_heavy_share", "rescued_light_share"] + H2_METRICS + [
    "e1_abandonment", "e2_duplicate", "collective_return", "steps", "exhausted", "horizon", "coverage"]
PAIRS = [(a, b) for i, a in enumerate(LEVELS) for b in LEVELS[i + 1:]]


def load(kind: str) -> pd.DataFrame:
    return pd.concat([pd.read_csv(f) for f in sorted((EVAL / kind).glob("*.csv"))], ignore_index=True)


def seed_table(df: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    rows = []
    for k, g in df.groupby(keys, sort=False):
        k = k if isinstance(k, tuple) else (k,)
        rows.append({**dict(zip(keys, k)), "episodes": len(g), **summarize_eval(g.to_dict("records"))})
    return pd.DataFrame(rows)


def matrix(SL: pd.DataFrame, block: str, metric: str, checkpoint: str = "final", levels=LEVELS) -> np.ndarray:
    d = SL[(SL.block == block) & (SL.checkpoint == checkpoint)].set_index(["seed", "level"])[metric]
    return np.array([[d.get((s, l), np.nan) for l in levels] for s in SEEDS], dtype=float)


def rnd(x, k=6):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), k)


def main() -> None:
    global OUT
    if "--out" in sys.argv:            # used by verify_results.py to reproduce every output in a scratch directory
        OUT = Path(sys.argv[sys.argv.index("--out") + 1])
    OUT.mkdir(parents=True, exist_ok=True)
    L = load("learned")
    SL = seed_table(L, ["block", "level", "checkpoint", "seed"])
    SL.to_csv(OUT / "seed_level_learned.csv", index=False)
    B = load("baselines")
    SB = seed_table(B, ["combo", "level", "policy"])
    SB.to_csv(OUT / "baselines_test.csv", index=False)
    base = SB.set_index(["combo", "level", "policy"])
    res: dict = {"n_boot": N_BOOT, "seeds": SEEDS}

    # ------------------------------------------------------------------ condition means with 95% CIs (all blocks)
    cm = []
    for (block, ckpt, level), g in SL.groupby(["block", "checkpoint", "level"]):
        for m in REPORT_METRICS:
            v = g.sort_values("seed")[m].values
            lo, hi = bootstrap_ci(v, f"cm|{block}|{ckpt}|{level}|{m}")
            cm.append({"block": block, "checkpoint": ckpt, "level": level, "metric": m,
                       "n": int(np.sum(~np.isnan(v))), "mean": np.nanmean(v), "ci_lo": lo, "ci_hi": hi,
                       "sd": np.nanstd(v, ddof=1), "min": np.nanmin(v), "max": np.nanmax(v)})
    CM = pd.DataFrame(cm)
    CM.to_csv(OUT / "condition_means.csv", index=False)

    # ------------------------------------------------------------------ H0 gate
    rf = matrix(SL, "main", "rf")
    g0 = one_sample_vs_constant(rf[:, 0], float(base.loc[("main", "Abundant", "random"), "rf"]), "greater")
    g0["passed"] = bool(g0["p"] < 0.05 and g0["delta_1"] >= 0.33)
    g0["random_rf"] = float(base.loc[("main", "Abundant", "random"), "rf"])
    res["H0"] = g0

    # ------------------------------------------------------------------ H1 + H2 omnibus and pairwise
    omni, pair_rows = [], []
    for fam, metrics in (("H1", ["rf"]), ("H2", H2_METRICS)):
        fr = [friedman(matrix(SL, "main", m)) for m in metrics]
        pg = [page_two_sided(matrix(SL, "main", m)) for m in metrics]
        fadj = holm([f["p"] for f in fr]) if fam == "H2" else [fr[0]["p"]]
        padj = holm([p["p"] for p in pg]) if fam == "H2" else [pg[0]["p"]]
        for m, f, p, fa, pa in zip(metrics, fr, pg, fadj, padj):
            M = matrix(SL, "main", m)
            kw = kruskal([M[:, j] for j in range(4)])
            omni.append({"family": fam, "metric": m, "n_complete": f["n"], "friedman_chi2": f["chi2"], "df": 3,
                         "friedman_p": f["p"], "friedman_p_holm": fa, "kendall_w": f["kendall_w"],
                         "page_L_dec": p["L_dec"], "page_p_dec": p["p_dec"], "page_p_inc": p["p_inc"],
                         "page_p_two_sided": p["p"], "page_p_holm": pa, "trend_direction": p["direction"],
                         "secondary_kw_H": kw["H"], "secondary_kw_p": kw["p"]})
            pv = []
            tmp = []
            for a, b in PAIRS:
                ia, ib = LEVELS.index(a), LEVELS.index(b)
                keep = ~np.isnan(M[:, ia]) & ~np.isnan(M[:, ib])
                w = wilcoxon_test(M[keep, ia] - M[keep, ib])
                lo, hi = paired_bootstrap_ci(M[keep, ia], M[keep, ib], f"pair|{m}|{a}|{b}")
                tmp.append({"family": fam, "metric": m, "pair": f"{a} - {b}", "n": int(keep.sum()),
                            "mean_diff": w["mean_diff"], "ci_lo": lo, "ci_hi": hi, "median_diff": w["median_diff"],
                            "r_rb": w["r_rb"], "p": w["p"], "method": w["method"],
                            "secondary_cliffs_delta": cliffs_delta(M[:, ia], M[:, ib])})
                pv.append(w["p"])
            for row, pa in zip(tmp, holm(pv)):
                row["p_holm6"] = pa
                pair_rows.append(row)
    OM, PW = pd.DataFrame(omni), pd.DataFrame(pair_rows)
    OM.to_csv(OUT / "h1_h2_omnibus.csv", index=False)
    PW.to_csv(OUT / "h1_h2_pairwise.csv", index=False)

    # ------------------------------------------------------------------ H3 IQL vs baselines
    h3 = []
    for level in LEVELS:
        x = rf[:, LEVELS.index(level)]
        for bl in ("random", "greedy", "cooperative"):
            c = float(base.loc[("main", level, bl), "rf"])
            t = one_sample_vs_constant(x, c)
            lo, hi = bootstrap_ci(x - c, f"h3|{level}|{bl}")
            h3.append({"level": level, "baseline": bl, "baseline_rf": c, "iql_mean_rf": float(x.mean()),
                       "mean_diff": t["mean_diff"], "ci_lo": lo, "ci_hi": hi, "median_diff": t["median_diff"],
                       "n_above": t["n_above"], "n_below": t["n_below"], "delta_1": t["delta_1"], "r_rb": t["r_rb"],
                       "p": t["p"], "method": t["method"]})
    H3 = pd.DataFrame(h3)
    H3["p_holm12"] = holm(H3.p.tolist())
    H3.to_csv(OUT / "h3_vs_baselines.csv", index=False)

    # ------------------------------------------------------------------ H4 (A1)
    A1 = seed_table(load("A1"), ["level", "round", "seed"])
    A1.to_csv(OUT / "seed_level_A1.csv", index=False)
    mm = A1.groupby(["level", "seed"]).rf.mean()
    h4 = []
    for level in LEVELS:
        o = rf[:, LEVELS.index(level)]
        x = np.array([mm[(level, s)] for s in SEEDS])
        w = wilcoxon_test(o - x)
        lo, hi = paired_bootstrap_ci(o, x, f"h4|{level}")
        h4.append({"level": level, "original_mean": o.mean(), "mismatch_mean": x.mean(), "mean_diff": w["mean_diff"],
                   "ci_lo": lo, "ci_hi": hi, "median_diff": w["median_diff"], "seeds_original_better":
                   int((o > x).sum()), "r_rb": w["r_rb"], "p": w["p"], "method": w["method"],
                   "relative_drop": float((o.mean() - x.mean()) / o.mean())})
    H4 = pd.DataFrame(h4)
    H4["p_holm4"] = holm(H4.p.tolist())
    H4.to_csv(OUT / "h4_A1_mismatch.csv", index=False)

    # ------------------------------------------------------------------ H5 (A3) + secondary analyses
    def oracle(combo, level):
        return float(base.loc[(combo, level, "oracle"), "rf"])

    def did(block_a, block_b, combo_a=None, combo_b=None, upto="Critical"):
        """Per-seed [x(Ab) - x(level)]_a - [x(Ab) - x(level)]_b; normalised if combos given."""
        Ma, Mb = matrix(SL, block_a, "rf"), matrix(SL, block_b, "rf")
        if combo_a:
            Ma = Ma / np.array([oracle(combo_a, l) for l in LEVELS])
            Mb = Mb / np.array([oracle(combo_b, l) for l in LEVELS])
        j = LEVELS.index(upto)
        return (Ma[:, 0] - Ma[:, j]) - (Mb[:, 0] - Mb[:, j]), Ma, Mb

    d5, _, _ = did("main", "p0")
    w5 = wilcoxon_test(d5)
    lo, hi = bootstrap_ci(d5, "h5|primary")
    res["H5"] = {"did_per_seed": d5.tolist(), "mean_did": float(d5.mean()), "ci_lo": lo, "ci_hi": hi,
                 "median_did": w5["median_diff"], "seeds_positive": int((d5 > 0).sum()), "r_rb": w5["r_rb"],
                 "p": w5["p"], "method": w5["method"]}
    a3 = []
    for label, (ba, bb, ca, cb) in {"raw_primary": ("main", "p0", None, None),
                                    "oracle_normalised_primary": ("main", "p0", "main", "p0"),
                                    "raw_secondary_own_calibration": ("main", "p0sec", None, None),
                                    "oracle_normalised_secondary": ("main", "p0sec", "main", "p0sec")}.items():
        for lvl in LEVELS[1:]:
            d, Ma, Mb = did(ba, bb, ca, cb, lvl)
            lo, hi = bootstrap_ci(d, f"a3|{label}|{lvl}")
            a3.append({"analysis": label, "level_vs_abundant": lvl, "mean_did": d.mean(), "ci_lo": lo, "ci_hi": hi,
                       "seeds_positive": int((d > 0).sum()),
                       "drop_p05_mean": float((Ma[:, 0] - Ma[:, LEVELS.index(lvl)]).mean()),
                       "drop_p0_mean": float((Mb[:, 0] - Mb[:, LEVELS.index(lvl)]).mean()),
                       "retained_p05": float(Ma[:, LEVELS.index(lvl)].mean() / Ma[:, 0].mean()),
                       "retained_p0": float(Mb[:, LEVELS.index(lvl)].mean() / Mb[:, 0].mean())})
    # POST HOC exploratory (added after seeing H5; deviations C4, sign fixed in C5): DiD of the LOG DROP, i.e. the same
    # convention as the raw DiD: [log RF(Ab) - log RF(level)]_{p=0.5} - [log RF(Ab) - log RF(level)]_{p=0}.
    # Positive = scarcity removes a larger FRACTION in the heavy-victim world.
    for label, bb in (("posthoc_log_ratio_primary", "p0"), ("posthoc_log_ratio_secondary", "p0sec")):
        Ma, Mb = matrix(SL, "main", "rf"), matrix(SL, bb, "rf")
        for lvl in LEVELS[1:]:
            j = LEVELS.index(lvl)
            d = np.log(Ma[:, 0] / Ma[:, j]) - np.log(Mb[:, 0] / Mb[:, j])
            lo, hi = bootstrap_ci(d, f"a3|{label}|{lvl}")
            w = wilcoxon_test(d)
            a3.append({"analysis": label, "level_vs_abundant": lvl, "mean_did": d.mean(), "ci_lo": lo, "ci_hi": hi,
                       "seeds_positive": int((d > 0).sum()), "p_unadjusted_exploratory": w["p"],
                       "retained_p05": float(np.exp(np.log(Ma[:, j] / Ma[:, 0]).mean())),
                       "retained_p0": float(np.exp(np.log(Mb[:, j] / Mb[:, 0]).mean()))})
    A3 = pd.DataFrame(a3)
    A3.to_csv(OUT / "a3_did_all.csv", index=False)
    res["A3_oracle"] = {c: {l: oracle(c, l) for l in LEVELS} for c in ("main", "p0", "p0sec")}

    # ------------------------------------------------------------------ H6 (A4)
    solo = matrix(SL, "solo", "rf")
    h6 = []
    for j, level in enumerate(LEVELS):
        w = wilcoxon_test(rf[:, j] - solo[:, j])
        lo, hi = paired_bootstrap_ci(rf[:, j], solo[:, j], f"h6|{level}")
        h6.append({"level": level, "joint_mean": rf[:, j].mean(), "solo_mean": solo[:, j].mean(),
                   "mean_diff": w["mean_diff"], "ci_lo": lo, "ci_hi": hi, "median_diff": w["median_diff"],
                   "seeds_joint_better": int((rf[:, j] > solo[:, j]).sum()), "r_rb": w["r_rb"], "p": w["p"],
                   "method": w["method"]})
    H6 = pd.DataFrame(h6)
    H6["p_holm4"] = holm(H6.p.tolist())
    H6.to_csv(OUT / "h6_A4_solo.csv", index=False)

    # ------------------------------------------------------------------ Secondary sensitivities of H1
    sens = {}
    bv = matrix(SL, "main", "rf", "bestval")
    sens["bestval_friedman"] = friedman(bv)
    sens["bestval_page"] = page_two_sided(bv)
    runs = pd.read_csv(ROOT / "results" / "phase5" / "training_runs.csv")  # built from run.json files (Phase 5)
    sens["stable_runs_total"] = int(runs.stable.sum())
    sens["runs_total"] = int(len(runs))
    sens["stable_by_block_level"] = runs.groupby(["block", "level"]).stable.sum().astype(int).reset_index().to_dict("records")
    main_stable = runs[(runs.block == "main") & runs.stable]
    sens["main_stable_runs"] = int(len(main_stable))
    sens["stable_only_H1"] = ("not computable: 0 of 40 main-block runs meet the preregistered stability criterion"
                              if len(main_stable) == 0 else "see table")
    res["sensitivity"] = sens

    # ------------------------------------------------------------------ Exploratory
    ex = []

    def paired_row(name, level, a, b, label):
        keep = ~np.isnan(a) & ~np.isnan(b)
        w = wilcoxon_test(a[keep] - b[keep])
        lo, hi = paired_bootstrap_ci(a[keep], b[keep], label)
        return {"analysis": name, "level": level, "n": int(keep.sum()), "mean_a": float(a[keep].mean()),
                "mean_b": float(b[keep].mean()), "mean_diff": w["mean_diff"], "ci_lo": lo, "ci_hi": hi,
                "r_rb": w["r_rb"], "p_unadjusted": w["p"]}

    A2 = seed_table(load("A2"), ["level", "policy", "seed", "ablated_slot", "replacement"])
    A2.to_csv(OUT / "seed_level_A2.csv", index=False)
    iq = A2[A2.policy == "iql"].groupby(["level", "replacement", "seed"])[["rf", "cr"]].mean()
    for j, level in enumerate(LEVELS):
        for rep in ("random", "wait"):
            ab = np.array([iq.loc[(level, rep, s), "rf"] for s in SEEDS])
            ex.append(paired_row(f"A2 RF intact - ablated ({rep})", level, rf[:, j], ab, f"a2|{level}|{rep}"))
            abc = np.array([iq.loc[(level, rep, s), "cr"] for s in SEEDS])
            ex.append(paired_row(f"A2 CR intact - ablated ({rep})", level, matrix(SL, "main", "cr")[:, j], abc,
                                 f"a2cr|{level}|{rep}"))
    coop = A2[A2.policy == "cooperative"].groupby(["level", "replacement"])[["rf", "cr"]].mean()
    coop.reset_index().to_csv(OUT / "a2_cooperative_baseline.csv", index=False)
    eq = matrix(SL, "eqsteps", "rf")
    for j, level in enumerate(LEVELS[1:], start=1):
        ex.append(paired_row("A6 RF equal-steps - equal-episodes", level, eq[:, j], rf[:, j], f"a6|{level}"))
    eqm = np.column_stack([rf[:, 0], eq[:, 1:]])
    res["A6_equal_steps_trend"] = {"friedman": friedman(eqm), "page": page_two_sided(eqm)}
    pooled = matrix(SL, "pooled", "rf")
    for j, level in enumerate(LEVELS):
        ex.append(paired_row("Pooled - per-agent RF", level, pooled[:, j], rf[:, j], f"pool|{level}"))
    sh = seed_table(load("shifted"), ["level", "seed"]).set_index(["seed", "level"]).rf
    shm = np.array([[sh[(s, l)] for l in LEVELS] for s in SEEDS])
    for j, level in enumerate(LEVELS):
        ex.append(paired_row("Shifted test - same-distribution test RF", level, shm[:, j], rf[:, j], f"sh|{level}"))
    for name, M in (("pooled", pooled), ("alt", matrix(SL, "alt", "rf")), ("p0", matrix(SL, "p0", "rf")),
                    ("p0sec", matrix(SL, "p0sec", "rf")), ("shifted", shm)):
        res[f"trend_{name}"] = {"friedman": friedman(M), "page": page_two_sided(M)}
    EX = pd.DataFrame(ex)
    EX.to_csv(OUT / "exploratory_paired.csv", index=False)

    TR = seed_table(load("transfer"), ["train_level", "test_level", "seed"])
    TR.to_csv(OUT / "seed_level_transfer.csv", index=False)
    tm = []
    for (a, b), g in TR.groupby(["train_level", "test_level"]):
        v = g.sort_values("seed").rf.values
        lo, hi = bootstrap_ci(v, f"tr|{a}|{b}")
        tm.append({"train_level": a, "test_level": b, "mean_rf": v.mean(), "ci_lo": lo, "ci_hi": hi})
    pd.DataFrame(tm).to_csv(OUT / "transfer_matrix.csv", index=False)

    # Exp4: E1, E2, E3 and individual vs collective
    e4 = []
    for level in LEVELS:
        rows = L[(L.block == "main") & (L.checkpoint == "final") & (L.level == level)].to_dict("records")
        flags = np.array(e3_conflict_flags(rows, 3))
        df = pd.DataFrame(rows).assign(e3=flags)
        per_seed = df.groupby("seed").agg(e3=("e3", "mean"), e1=("e1_abandonment", "mean"),
                                          e2=("e2_duplicate", "mean"))
        ind = df[["return_agent0", "return_agent1", "return_agent2"]].values
        rho = ss.spearmanr(ind.max(axis=1), df.collective_return).statistic
        for m in ("e1", "e2", "e3"):
            lo, hi = bootstrap_ci(per_seed[m].values, f"e4|{level}|{m}")
            e4.append({"level": level, "measure": m, "mean_per_seed": per_seed[m].mean(), "ci_lo": lo, "ci_hi": hi})
        e4.append({"level": level, "measure": "spearman(best individual return, collective return)",
                   "mean_per_seed": rho, "ci_lo": np.nan, "ci_hi": np.nan})
    pd.DataFrame(e4).to_csv(OUT / "exp4_individual_collective.csv", index=False)

    # ------------------------------------------------------------------ A8 mediation (association only)
    preds = ["ear", "rsr_other", "tdi", "pss", "gini_consumption", "cr"]
    D = SL[(SL.block == "main") & (SL.checkpoint == "final")][["seed", "level", "rf"] + preds].copy()
    n_all = len(D)
    D = D.dropna().reset_index(drop=True)
    Zraw = D[preds].values
    mu, sd = Zraw.mean(axis=0), Zraw.std(axis=0, ddof=0)
    Z = (Zraw - mu) / sd
    dummies = np.column_stack([(D.level == l).astype(float) for l in LEVELS[1:]])
    X = np.column_stack([np.ones(len(D)), Z, dummies])
    beta = ols(D.rf.values, X)
    resid = D.rf.values - X @ beta
    r2 = 1 - resid.var() / D.rf.values.var()
    X0 = np.column_stack([np.ones(len(D)), dummies])
    r2_levels = 1 - (D.rf.values - X0 @ ols(D.rf.values, X0)).var() / D.rf.values.var()
    rng = np.random.default_rng(np.random.SeedSequence(0xA8))
    seeds_present = sorted(D.seed.unique())
    boots = []
    for _ in range(N_BOOT):
        pick = rng.choice(seeds_present, size=len(seeds_present), replace=True)
        idx = np.concatenate([np.flatnonzero(D.seed.values == s) for s in pick])
        boots.append(ols(D.rf.values[idx], X[idx]))
    boots = np.array(boots)
    med = []
    for k, name in enumerate(["intercept"] + preds + [f"level_{l}" for l in LEVELS[1:]]):
        med.append({"model": "joint", "term": name, "coef": beta[k], "ci_lo": np.quantile(boots[:, k], 0.025),
                    "ci_hi": np.quantile(boots[:, k], 0.975)})
    for j, m in enumerate(preds):          # one metric at a time + level dummies
        Xm = np.column_stack([np.ones(len(D)), Z[:, j], dummies])
        bm = ols(D.rf.values, Xm)
        bb = []
        rng2 = np.random.default_rng(np.random.SeedSequence([0xA8, j]))
        for _ in range(N_BOOT):
            pick = rng2.choice(seeds_present, size=len(seeds_present), replace=True)
            idx = np.concatenate([np.flatnonzero(D.seed.values == s) for s in pick])
            bb.append(ols(D.rf.values[idx], Xm[idx])[1])
        within = [ss.spearmanr(D[D.level == l][m], D[D.level == l].rf).statistic for l in LEVELS]
        med.append({"model": "single", "term": m, "coef": bm[1], "ci_lo": np.quantile(bb, 0.025),
                    "ci_hi": np.quantile(bb, 0.975),
                    "within_level_spearman": ";".join(f"{l}:{r:.3f}" for l, r in zip(LEVELS, within))})
    MED = pd.DataFrame(med)
    MED.to_csv(OUT / "a8_mediation.csv", index=False)
    res["A8"] = {"n_obs": int(len(D)), "n_excluded_undefined_ear": int(n_all - len(D)), "r2_joint": float(r2),
                 "r2_levels_only": float(r2_levels), "vif": dict(zip(preds, vif(Z))),
                 "note": "Observational association across seeds; not causal evidence."}

    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=lambda o: rnd(o, 10)))
    print(json.dumps({"H0": res["H0"], "H5": {k: v for k, v in res["H5"].items() if k != "did_per_seed"},
                      "A8": res["A8"]}, indent=1, default=str))


if __name__ == "__main__":
    main()
