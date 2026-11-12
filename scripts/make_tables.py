"""Phase 6 tables (results/tables/*.md, *.csv) and the statistics summary (results/stats/stats_summary.md), built only
from results/stats outputs. Every table states its family: CONFIRMATORY / SECONDARY / EXPLORATORY / POST HOC.
Usage: python scripts/make_tables.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from tlr.experiments import LEVELS  # noqa: E402

ST = ROOT / "results" / "stats"
TB = ROOT / "results" / "tables"


def ci(m, lo, hi, k=3):
    return f"{m:.{k}f} [{lo:.{k}f}, {hi:.{k}f}]"


def pf(p):
    if p is None or (isinstance(p, float) and np.isnan(p)):
        return "–"
    return f"{p:.2e}" if p < 0.001 else f"{p:.4f}"


def lv(df, col="level"):
    return df.assign(_o=df[col].map({l: i for i, l in enumerate(LEVELS)})).sort_values("_o").drop(columns="_o")


def write(name: str, df: pd.DataFrame, title: str) -> str:
    TB.mkdir(parents=True, exist_ok=True)
    df.to_csv(TB / f"{name}.csv", index=False)
    md = f"### {title}\n\n" + df.to_markdown(index=False) + "\n"
    (TB / f"{name}.md").write_text(md)
    return md


def main() -> None:
    r = json.loads((ST / "results.json").read_text())
    CM = pd.read_csv(ST / "condition_means.csv")
    OM = pd.read_csv(ST / "h1_h2_omnibus.csv")
    PW = pd.read_csv(ST / "h1_h2_pairwise.csv")
    H3 = pd.read_csv(ST / "h3_vs_baselines.csv")
    H4 = pd.read_csv(ST / "h4_A1_mismatch.csv")
    H6 = pd.read_csv(ST / "h6_A4_solo.csv")
    A3 = pd.read_csv(ST / "a3_did_all.csv")
    EX = pd.read_csv(ST / "exploratory_paired.csv")
    MED = pd.read_csv(ST / "a8_mediation.csv")
    E4 = pd.read_csv(ST / "exp4_individual_collective.csv")
    TR = pd.read_csv(ST / "transfer_matrix.csv")
    SB = pd.read_csv(ST / "baselines_test.csv")
    out = ["# Phase 6 statistics summary", "",
           "Unit = training seed (n = 10 per condition unless stated). Values: mean [95% percentile bootstrap CI, 10,000 "
           "resamples of seeds]. Paired tests across conditions (seeds matched). Holm corrections within the "
           "preregistered families. All 10 seeds analysed; unstable runs included. Performance is after 8,000 "
           "training episodes, not converged. The oracle is a full-information reference, never a learner. Families: "
           "CONFIRMATORY (preregistered H0-H6), SECONDARY (preregistered, reported without inference or as "
           "robustness), EXPLORATORY (unadjusted p), POST HOC (added after seeing results; deviations C4/C5).", ""]

    # T1
    m = CM[(CM.block == "main") & (CM.checkpoint == "final")]
    rows = []
    for level in LEVELS:
        g = m[m.level == level].set_index("metric")
        rows.append({"level": level, **{k: ci(g.loc[k, "mean"], g.loc[k, "ci_lo"], g.loc[k, "ci_hi"]) for k in
                                        ("rf", "rescued_heavy_share", "rescued_light_share", "cr", "ear", "tdi",
                                         "rsr_other", "pss", "gini_consumption")}})
    out.append(write("T1_main_condition_means", pd.DataFrame(rows),
                     "T1. Exp1/Exp2 main sweep, test set, final checkpoint: mean [95% CI] (n = 10; EAR n = 9 at Scarce "
                     "and Critical)"))
    # Baselines
    sb = lv(SB[SB.combo == "main"])[["level", "policy", "rf", "rescued_heavy_share", "cr"]].round(3)
    out.append(write("T1b_baselines_main", sb, "T1b. Baselines and oracle reference on the same 100 test instances "
                                                 "(oracle = full information, not a learner)"))
    # T2 H0 + H1/H2
    h0 = r["H0"]
    out += ["### T2a. H0-gate (CONFIRMATORY)", "",
            f"IQL RF at Abundant vs random ({h0['random_rf']:.3f}): {h0['n_above']}/10 seeds above, one-sided Wilcoxon "
            f"W+ = {h0['W_plus']:.0f}, exact p = {pf(h0['p'])}, δ₁ = {h0['delta_1']:.2f}, median difference "
            f"{h0['median_diff']:.3f}. **Gate {'PASSED' if h0['passed'] else 'FAILED'}.**", ""]
    t2 = OM.assign(friedman=OM.apply(lambda x: f"χ²(3) = {x.friedman_chi2:.2f}, p = {pf(x.friedman_p)}", axis=1),
                   holm_friedman=OM.friedman_p_holm.map(pf), kendall_w=OM.kendall_w.round(3),
                   page_two_sided=OM.page_p_two_sided.map(pf), holm_page=OM.page_p_holm.map(pf),
                   KW_secondary=OM.secondary_kw_p.map(pf))[
        ["family", "metric", "n_complete", "friedman", "holm_friedman", "kendall_w", "page_two_sided", "holm_page",
         "trend_direction", "KW_secondary"]]
    out.append(write("T2_h1_h2_omnibus", t2, "T2b. H1 and H2 (CONFIRMATORY): Friedman and Page's L across the four "
                                              "levels; Holm across the 7 H2 metrics; Kruskal-Wallis = SECONDARY"))
    t3 = PW.assign(diff=PW.apply(lambda x: ci(x.mean_diff, x.ci_lo, x.ci_hi), axis=1), r_rb=PW.r_rb.round(2),
                   p_raw=PW.p.map(pf), p_holm6=PW.p_holm6.map(pf),
                   cliffs_delta_secondary=PW.secondary_cliffs_delta.round(2))[
        ["family", "metric", "pair", "n", "diff", "r_rb", "p_raw", "p_holm6", "cliffs_delta_secondary"]]
    out.append(write("T3_pairwise", t3, "T3. Pairwise level comparisons (CONFIRMATORY follow-ups): paired Wilcoxon, "
                                        "Holm across 6 pairs within metric; difference = first minus second level"))
    t4 = H3.assign(diff=H3.apply(lambda x: ci(x.mean_diff, x.ci_lo, x.ci_hi), axis=1), p=H3.p.map(pf),
                   p_holm12=H3.p_holm12.map(pf), baseline_rf=H3.baseline_rf.round(3),
                   iql_mean_rf=H3.iql_mean_rf.round(3))[
        ["level", "baseline", "baseline_rf", "iql_mean_rf", "diff", "n_above", "delta_1", "p", "p_holm12"]]
    out.append(write("T4_h3_vs_baselines", t4, "T4. H3 (CONFIRMATORY): IQL vs each baseline, one-sample Wilcoxon "
                                                "(two-sided), Holm across 12"))
    t5 = pd.concat([
        H4.assign(test="H4 / A1 original - mismatched", diff=H4.apply(lambda x: ci(x.mean_diff, x.ci_lo, x.ci_hi),
                                                                      axis=1),
                  seeds=H4.seeds_original_better, p_=H4.p.map(pf), holm=H4.p_holm4.map(pf))[
            ["test", "level", "diff", "seeds", "r_rb", "p_", "holm"]],
        H6.assign(test="H6 / A4 joint - solo", diff=H6.apply(lambda x: ci(x.mean_diff, x.ci_lo, x.ci_hi), axis=1),
                  seeds=H6.seeds_joint_better, p_=H6.p.map(pf), holm=H6.p_holm4.map(pf), r_rb=1.0)[
            ["test", "level", "diff", "seeds", "r_rb", "p_", "holm"]]])
    t5 = t5.rename(columns={"p_": "p_raw", "holm": "p_holm4", "seeds": "seeds_in_direction"})
    t5["r_rb"] = t5.r_rb.astype(float).round(2)
    out.append(write("T5_h4_h6_attribution", t5, "T5. H4 and H6 (CONFIRMATORY): paired by seed, Holm across the 4 "
                                                 "levels (H6 caveat: solo agents never observed a teammate in training)"))
    h5 = r["H5"]
    out += ["### T6a. H5 / A3 primary (CONFIRMATORY)", "",
            f"DiD = [RF(Ab) − RF(Cr)]_heavy − [RF(Ab) − RF(Cr)]_all-light (main budgets in both worlds): "
            f"mean {ci(h5['mean_did'], h5['ci_lo'], h5['ci_hi'])}, median {h5['median_did']:.3f}, "
            f"{h5['seeds_positive']}/10 seeds positive, Wilcoxon exact p = {pf(h5['p'])}, r_rb = {h5['r_rb']:.2f}. "
            "Negative = the all-light world loses MORE rescue-fraction points.", ""]
    t6 = A3.assign(did=A3.apply(lambda x: ci(x.mean_did, x.ci_lo, x.ci_hi), axis=1),
                   family=A3.analysis.map(lambda a: "POST HOC exploratory" if a.startswith("posthoc") else
                                          ("CONFIRMATORY (Critical row = H5)" if a == "raw_primary" else
                                           "SECONDARY (estimate only)")))[
        ["family", "analysis", "level_vs_abundant", "did", "seeds_positive", "retained_p05", "retained_p0"]]
    t6["retained_p05"] = t6.retained_p05.round(3)
    t6["retained_p0"] = t6.retained_p0.round(3)
    out.append(write("T6_a3_did", t6, "T6b. A3 difference-in-differences, all analyses (positive = scarcity removes "
                                      "more, in points or log-fraction, in the heavy-victim world); retained = "
                                      "RF(level)/RF(Abundant)"))
    t7 = EX.assign(diff=EX.apply(lambda x: ci(x.mean_diff, x.ci_lo, x.ci_hi), axis=1),
                   p_unadjusted=EX.p_unadjusted.map(pf), mean_a=EX.mean_a.round(3), mean_b=EX.mean_b.round(3),
                   r_rb=EX.r_rb.round(2))[["analysis", "level", "n", "mean_a", "mean_b", "diff", "r_rb", "p_unadjusted"]]
    out.append(write("T7_exploratory_paired", t7, "T7. EXPLORATORY paired contrasts (A2, A6, pooled, shifted test); "
                                                  "unadjusted p"))
    tr = []
    for k in ("A6_equal_steps_trend", "trend_pooled", "trend_alt", "trend_p0", "trend_p0sec", "trend_shifted"):
        tr.append({"analysis": k, "friedman_chi2": round(r[k]["friedman"]["chi2"], 2),
                   "friedman_p": pf(r[k]["friedman"]["p"]), "kendall_w": round(r[k]["friedman"]["kendall_w"], 3),
                   "page_two_sided_p": pf(r[k]["page"]["p"]), "direction": r[k]["page"]["direction"]})
    s = r["sensitivity"]
    tr.append({"analysis": "SECONDARY best-validation checkpoint (H1)", "friedman_chi2": round(s["bestval_friedman"]["chi2"], 2),
               "friedman_p": pf(s["bestval_friedman"]["p"]), "kendall_w": round(s["bestval_friedman"]["kendall_w"], 3),
               "page_two_sided_p": pf(s["bestval_page"]["p"]), "direction": s["bestval_page"]["direction"]})
    out.append(write("T8_trend_robustness", pd.DataFrame(tr), "T8. Scarcity trend in robustness variants "
                                                              "(EXPLORATORY) and best-validation sensitivity (SECONDARY)"))
    out += ["### T9. Stable-run sensitivity (SECONDARY)", "",
            f"{s['stable_runs_total']} of {s['runs_total']} training runs meet the preregistered stability criterion; "
            f"main block: {s['main_stable_runs']} of 40. {s['stable_only_H1']}. Stable runs by block: " +
            ", ".join(f"{d['block']}/{d['level']} {d['stable']}" for d in s["stable_by_block_level"] if d["stable"]) +
            ".", ""]
    med = MED.assign(coef_ci=MED.apply(lambda x: ci(x.coef, x.ci_lo, x.ci_hi, 4), axis=1))[
        ["model", "term", "coef_ci", "within_level_spearman"]].fillna("")
    a8 = r["A8"]
    out.append(write("T10_a8_mediation", med,
                     f"T10. A8 (EXPLORATORY, observational association): OLS of seed RF on standardized metrics + level "
                     f"dummies; cluster bootstrap over seeds. n = {a8['n_obs']} (excluded {a8['n_excluded_undefined_ear']} "
                     f"with undefined EAR); R² levels only {a8['r2_levels_only']:.3f}, joint {a8['r2_joint']:.3f}; VIF " +
                     ", ".join(f"{k} {v:.1f}" for k, v in a8["vif"].items())))
    e4 = E4.assign(value=E4.apply(lambda x: f"{x.mean_per_seed:.3f}" if np.isnan(x.ci_lo) else
                                  ci(x.mean_per_seed, x.ci_lo, x.ci_hi), axis=1))[["level", "measure", "value"]]
    out.append(write("T11_exp4", e4, "T11. Exp4 individual vs collective (EXPLORATORY): E1 abandonment and E2 duplicate "
                                     "rescues per episode; E3 conflict share; Spearman of best individual vs collective "
                                     "return across episodes"))
    tm = TR.assign(rf=TR.apply(lambda x: ci(x.mean_rf, x.ci_lo, x.ci_hi), axis=1)).pivot(
        index="train_level", columns="test_level", values="rf").loc[LEVELS, LEVELS].reset_index()
    out.append(write("T12_transfer", tm, "T12. Exp5 cross-ρ transfer matrix (EXPLORATORY): rows trained at, columns "
                                         "tested at, mean RF [95% CI]"))
    (ST / "stats_summary.md").write_text("\n".join(out))
    print(f"{len(list(TB.glob('*.md')))} tables -> {TB.relative_to(ROOT)}; summary -> results/stats/stats_summary.md")


if __name__ == "__main__":
    main()
