"""Phase 6 figures from saved results only (results/stats, results/runs). Re-runnable; no computation of new statistics
beyond means and the preregistered bootstrap CIs (tlr.stats).

Conventions: rho levels always ordered Abundant -> Critical; ordinal blue ramp for levels (validated); categorical palette
for methods (validated in Phase 3); error bars / bands = 95% percentile bootstrap CI over the 10 seeds; thin lines =
individual seeds (paired across levels); the oracle is drawn as a separate, labelled reference, never as a learner.
Outputs: results/figures/fig*.png
Usage: python scripts/make_figures.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from tlr.experiments import LEVELS, SEEDS, run_dir  # noqa: E402
from tlr.stats import bootstrap_ci  # noqa: E402

ST = ROOT / "results" / "stats"
FIG = ROOT / "results" / "figures"
LEVEL_C = {"Abundant": "#86b6ef", "Moderate": "#3987e5", "Scarce": "#1c5cab", "Critical": "#0d366b"}
CAT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#6250d6"]
MK = ["o", "s", "^", "D", "v", "P"]
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"
X = np.arange(4)


def style(ax, title: str | None = None) -> None:
    ax.grid(True, axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(colors=MUTED, labelsize=8)
    if title:
        ax.set_title(title, fontsize=9, loc="left")


def level_axis(ax) -> None:
    ax.set_xticks(X)
    ax.set_xticklabels(LEVELS, fontsize=8)


def save(fig, name: str) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(FIG / name, dpi=160)
    plt.close(fig)


def mean_ci(SL, block, metric, ckpt="final"):
    d = SL[(SL.block == block) & (SL.checkpoint == ckpt)]
    M = np.array([[d[(d.seed == s) & (d.level == l)][metric].iloc[0] if len(d[(d.seed == s) & (d.level == l)]) else
                   np.nan for l in LEVELS] for s in SEEDS], dtype=float)
    m = np.nanmean(M, axis=0)
    ci = np.array([bootstrap_ci(M[:, j], f"fig|{block}|{metric}|{ckpt}|{l}") for j, l in enumerate(LEVELS)])
    return M, m, ci


def errbar(ax, x, m, ci, color, marker, label, **kw):
    ax.errorbar(x, m, yerr=[m - ci[:, 0], ci[:, 1] - m], color=color, marker=marker, markersize=6, linewidth=2,
                capsize=3, label=label, **kw)


def main() -> None:
    SL = pd.read_csv(ST / "seed_level_learned.csv")
    SB = pd.read_csv(ST / "baselines_test.csv")
    OM = pd.read_csv(ST / "h1_h2_omnibus.csv")
    base = SB.set_index(["combo", "level", "policy"])

    # ---------------- Fig 1: learning curves (validation) per level
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    for metric, ax, title in (("rf", axes[0], "Validation rescue fraction"),
                              ("rescued_heavy_share", axes[1], "Validation share of heavy victims rescued")):
        for level in LEVELS:
            cks = [pd.read_csv(run_dir("main", level, s) / "checkpoints.csv") for s in SEEDS]
            ep = cks[0].episode.values
            M = np.array([c[metric].values for c in cks])
            m = M.mean(axis=0)
            ci = np.array([bootstrap_ci(M[:, k], f"lc|{metric}|{level}|{k}") for k in range(M.shape[1])])
            ax.plot(ep, m, color=LEVEL_C[level], linewidth=2, label=level)
            ax.fill_between(ep, ci[:, 0], ci[:, 1], color=LEVEL_C[level], alpha=0.18, linewidth=0)
        ax.axvline(5600, color=MUTED, linestyle=":", linewidth=1)
        ax.text(5650, 0.95, "ε reaches 0.05", fontsize=7, color=INK, va="top")
        ax.set_xlabel("training episodes")
        ax.set_ylim(-0.02, 1.0)
        style(ax, title)
    axes[0].legend(frameon=False, fontsize=8, loc="upper left")
    fig.suptitle("Fig. 1  Learning curves of the main sweep (mean of 10 seeds, 95% CI band; greedy evaluation on 50 "
                 "validation instances every 500 episodes).\nLearning starts late and is not converged at 8,000 "
                 "episodes.", fontsize=9, x=0.01, ha="left")
    save(fig, "fig1_learning_curves.png")

    # ---------------- Fig 2: Exp1 RF and heavy/light shares vs baselines
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
    ax = axes[0]
    M, m, ci = mean_ci(SL, "main", "rf")
    for s in range(10):
        ax.plot(X, M[s], color=GRID, linewidth=1, zorder=1)
    errbar(ax, X, m, ci, CAT[0], MK[0], "IQL (10 seeds, mean ± 95% CI)", zorder=3)
    for j, (pol, lab) in enumerate((("cooperative", "Cooperative baseline"), ("greedy", "Greedy baseline"),
                                    ("random", "Random baseline")), start=2):
        ax.plot(X, [base.loc[("main", l, pol), "rf"] for l in LEVELS], color=CAT[j], marker=MK[j], linewidth=1.5,
                linestyle="--", label=lab)
    ax.plot(X, [base.loc[("main", l, "oracle"), "rf"] for l in LEVELS], color=CAT[1], marker=MK[1], linewidth=1.5,
            linestyle=":", label="Oracle reference (full information)")
    level_axis(ax)
    ax.set_ylabel("Rescue fraction (test, 100 instances)")
    ax.set_ylim(-0.02, 1.05)
    ax.legend(frameon=False, fontsize=7, loc="upper right")
    style(ax, "a) Rescue fraction falls monotonically with scarcity in every seed")
    ax = axes[1]
    for metric, c, mk, lab in (("rescued_light_share", CAT[2], MK[2], "Light victims (one agent)"),
                               ("rescued_heavy_share", CAT[0], MK[0], "Heavy victims (RESCUE + ASSIST)")):
        M, m, ci = mean_ci(SL, "main", metric)
        for s in range(10):
            ax.plot(X, M[s], color=c, alpha=0.15, linewidth=1)
        errbar(ax, X, m, ci, c, mk, lab)
    level_axis(ax)
    ax.set_ylabel("Share of victims of that type rescued")
    ax.set_ylim(-0.02, 1.05)
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    style(ax, "b) Heavy (cooperative) rescues collapse fastest")
    fig.suptitle("Fig. 2  Exp1: learned performance after 8,000 episodes by scarcity level (H1: Friedman χ²(3) = 30.0, "
                 "p = 1.4e-6, Kendall's W = 1.00; Page two-sided p = 3.2e-14).", fontsize=9, x=0.01, ha="left")
    save(fig, "fig2_exp1_rescue.png")

    # ---------------- Fig 3: Exp2 cooperation metrics (H2)
    names = {"ear": "C1 effective assist rate", "rsr": "C2 redundant search ratio", "rsr_other":
             "C2 redundant search (others)", "tdi": "C3 territory division", "pss": "C4a productive spend share*",
             "gini_consumption": "C4b consumption Gini", "cr": "C5 cooperation rate"}
    fig, axes = plt.subplots(2, 4, figsize=(13, 6.4))
    for ax, metric in zip(axes.flat, names):
        M, m, ci = mean_ci(SL, "main", metric)
        for s in range(10):
            ax.plot(X, M[s], color=GRID, linewidth=1)
        errbar(ax, X, m, ci, CAT[0], MK[0], None)
        o = OM[OM.metric == metric].iloc[0]
        level_axis(ax)
        style(ax, f"{names[metric]}\nFriedman Holm p = {o.friedman_p_holm:.2g}; n = {o.n_complete}")
    ax = axes.flat[-1]
    ax.axis("off")
    ax.text(0, 0.9, "Thin lines: individual seeds.\nMarkers: mean ± 95% bootstrap CI.\n\n"
                    "Holm across the 7 H2 metrics.\n\n* C4a tracks collective return almost\n"
                    "monotonically (Phase 2, D22) and is not\nindependent evidence of cooperation.\n\n"
                    "C1: seeds without any ASSIST are\nexcluded (complete blocks, n = 8).", fontsize=8, va="top",
            color=INK)
    fig.suptitle("Fig. 3  Exp2 / H2: cooperation metrics by scarcity (main, test). The cooperation rate falls sharply; "
                 "territory division, effective assists and load balance do not change significantly.", fontsize=9,
                 x=0.01, ha="left")
    save(fig, "fig3_exp2_cooperation.png")

    # ---------------- Fig 4: attribution (A1, A2, A4, A6)
    fig, axes = plt.subplots(1, 4, figsize=(15, 4.4), sharey=False)
    rf_M, rf_m, rf_ci = mean_ci(SL, "main", "rf")
    a1 = pd.read_csv(ST / "seed_level_A1.csv").groupby(["level", "seed"]).rf.mean()
    Mm = np.array([[a1[(l, s)] for l in LEVELS] for s in SEEDS])
    ci_m = np.array([bootstrap_ci(Mm[:, j], f"fig|a1|{l}") for j, l in enumerate(LEVELS)])
    ax = axes[0]
    errbar(ax, X - 0.08, rf_m, rf_ci, CAT[0], MK[0], "Original teams")
    errbar(ax, X + 0.08, Mm.mean(axis=0), ci_m, CAT[1], MK[1], "Mismatched teams")
    style(ax, "A1 / H4: teammates from other seeds")
    a2 = pd.read_csv(ST / "seed_level_A2.csv")
    a2 = a2[a2.policy == "iql"].groupby(["replacement", "level", "seed"]).rf.mean()
    ax = axes[1]
    errbar(ax, X - 0.1, rf_m, rf_ci, CAT[0], MK[0], "Intact team")
    for k, (rep, lab) in enumerate((("random", "One agent random"), ("wait", "One agent WAIT-only")), start=1):
        R = np.array([[a2[(rep, l, s)] for l in LEVELS] for s in SEEDS])
        errbar(ax, X + 0.1 * k - 0.0, R.mean(axis=0),
               np.array([bootstrap_ci(R[:, j], f"fig|a2|{rep}|{l}") for j, l in enumerate(LEVELS)]),
               CAT[k + 1], MK[k + 1], lab)
    style(ax, "A2: one agent replaced at test time")
    ax = axes[2]
    S, s_m, s_ci = mean_ci(SL, "solo", "rf")
    errbar(ax, X - 0.08, rf_m, rf_ci, CAT[0], MK[0], "Jointly trained")
    errbar(ax, X + 0.08, s_m, s_ci, CAT[4], MK[4], "Solo-trained, deployed together")
    style(ax, "A4 / H6: joint vs solo training\n(caveat: solo agents never saw a teammate)")
    ax = axes[3]
    E, e_m, e_ci = mean_ci(SL, "eqsteps", "rf")
    e_m[0], e_ci[0] = rf_m[0], rf_ci[0]
    errbar(ax, X - 0.08, rf_m, rf_ci, CAT[0], MK[0], "Equal episodes (8,000)")
    errbar(ax, X + 0.08, e_m, e_ci, CAT[5], MK[5], "Equal env. steps (A6)")
    style(ax, "A6: equal training data")
    for ax in axes:
        level_axis(ax)
        ax.set_ylim(-0.02, 0.8)
        ax.legend(frameon=False, fontsize=7, loc="upper right")
    axes[0].set_ylabel("Rescue fraction (test)")
    fig.suptitle("Fig. 4  Attribution checks (mean ± 95% CI over 10 seeds). Mismatching or removing teammates lowers "
                 "performance; the scarcity trend survives equal training steps.", fontsize=9, x=0.01, ha="left")
    save(fig, "fig4_attribution.png")

    # ---------------- Fig 5: A3
    A3 = pd.read_csv(ST / "a3_did_all.csv")
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
    ax = axes[0]
    for j, (block, combo, lab) in enumerate((("main", "main", "Heavy victims present (p_heavy = 0.5)"),
                                             ("p0", "p0", "All victims light (p_heavy = 0), same budgets"))):
        M, m, ci = mean_ci(SL, block, "rf")
        errbar(ax, X, m, ci, CAT[j], MK[j], lab)
        ax.plot(X, [base.loc[(combo, l, "oracle"), "rf"] for l in LEVELS], color=CAT[j], linestyle=":",
                linewidth=1.2, label=f"oracle reference, {'p_heavy 0.5' if j == 0 else 'p_heavy 0'}")
    level_axis(ax)
    ax.set_ylim(-0.02, 1.05)
    ax.set_ylabel("Rescue fraction (test)")
    ax.legend(frameon=False, fontsize=7, loc="lower left")
    style(ax, "a) Both worlds decline; the all-light world starts higher")
    ax = axes[1]
    series = [("raw_primary", "Raw DiD (primary, preregistered)"),
              ("oracle_normalised_primary", "Oracle-normalised DiD (secondary b)"),
              ("posthoc_log_ratio_primary", "Log-scale DiD of drops (POST HOC exploratory)")]
    for k, (an, lab) in enumerate(series):
        d = A3[A3.analysis == an].set_index("level_vs_abundant").loc[LEVELS[1:]]
        xs = np.arange(1, 4) + (k - 1) * 0.12
        ax.errorbar(xs, d.mean_did, yerr=[d.mean_did - d.ci_lo, d.ci_hi - d.mean_did], color=CAT[[0, 2, 4][k]],
                    marker=MK[k], linestyle="none", capsize=3, markersize=6, label=lab)
    ax.axhline(0, color=MUTED, linewidth=1)
    ax.set_xticks([1, 2, 3])
    ax.set_xticklabels([f"Abundant → {l}" for l in LEVELS[1:]], fontsize=8)
    ax.set_ylabel("Difference-in-differences (p_heavy 0.5 minus p_heavy 0)")
    ax.legend(frameon=False, fontsize=7, loc="upper left")
    style(ax, "b) Additive DiDs < 0; post hoc log DiD > 0 at Critical. The heavy world loses\nfewer POINTS but a "
              "larger FRACTION: the interaction is scale-dependent")
    fig.suptitle("Fig. 5  A3: cooperation-necessary vs cooperation-optional worlds (means ± 95% CI; positive DiD would "
                 "mean scarcity removes more, in points or in log-fraction, in the heavy-victim world).", fontsize=9, x=0.01, ha="left")
    save(fig, "fig5_a3_did.png")

    # ---------------- Fig 6: Exp5 transfer matrix and shifted test
    TM = pd.read_csv(ST / "transfer_matrix.csv").pivot(index="train_level", columns="test_level", values="mean_rf")
    TM = TM.loc[LEVELS, LEVELS]
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.4), gridspec_kw={"width_ratios": [1.1, 1]})
    ax = axes[0]
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("blue", ["#cde2fb", "#6da7ec", "#256abf", "#0d366b"])
    im = ax.imshow(TM.values, cmap=cmap, vmin=0, vmax=0.6)
    for i in range(4):
        for j in range(4):
            v = TM.values[i, j]
            ax.text(j, i, f"{v:.3f}", ha="center", va="center", fontsize=8, color="#fcfcfb" if v > 0.3 else INK,
                    fontweight="bold" if i == j else "normal")
    ax.set_xticks(range(4), LEVELS, fontsize=8)
    ax.set_yticks(range(4), LEVELS, fontsize=8)
    ax.set_xlabel("tested at")
    ax.set_ylabel("trained at")
    fig.colorbar(im, ax=ax, fraction=0.046, label="mean rescue fraction")
    ax.set_title("a) Cross-ρ transfer (diagonal bold = matched)", fontsize=9, loc="left")
    ax = axes[1]
    sh = pd.read_csv(ROOT / "results" / "phase5" / "seed_level_shifted.csv")
    Msh = np.array([[sh[(sh.seed == s) & (sh.level == l)].rf.iloc[0] for l in LEVELS] for s in SEEDS])
    errbar(ax, X - 0.08, rf_m, rf_ci, CAT[0], MK[0], "Same-distribution test")
    errbar(ax, X + 0.08, Msh.mean(axis=0),
           np.array([bootstrap_ci(Msh[:, j], f"fig|sh|{l}") for j, l in enumerate(LEVELS)]), CAT[1], MK[1],
           "Shifted test (walls 0.25, density 0.09)")
    level_axis(ax)
    ax.set_ylim(-0.02, 0.8)
    ax.set_ylabel("Rescue fraction")
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    style(ax, "b) Distribution shift lowers RF at every level")
    fig.suptitle("Fig. 6  Exp5 generalization. Policies trained with abundant budgets fail under scarcity; training at "
                 "an intermediate level transfers best to Critical.", fontsize=9, x=0.01, ha="left")
    save(fig, "fig6_exp5_generalization.png")

    # ---------------- Fig 7: A5 non-stationarity diagnostics
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.2))
    for level in LEVELS:
        cks = [pd.read_csv(run_dir("main", level, s) / "checkpoints.csv") for s in SEEDS]
        ep = cks[0].episode.values
        for ax, col in ((axes[0], "churn"), (axes[1], "train_mean_abs_td")):
            M = np.array([c[col].values for c in cks])
            ax.plot(ep, np.nanmean(M, axis=0), color=LEVEL_C[level], linewidth=2, label=level)
    axes[0].axhline(0.05, color=MUTED, linestyle="--", linewidth=1)
    axes[0].text(8000, 0.042, "5% stability threshold", fontsize=7, color=INK, ha="right", va="top")
    style(axes[0], "a) Policy churn between checkpoints (mean of 10 seeds)")
    style(axes[1], "b) Mean |TD error| over the preceding 500 episodes")
    for ax in axes[:2]:
        ax.set_xlabel("training episodes")
    axes[0].legend(frameon=False, fontsize=8)
    runs = pd.read_csv(ROOT / "results" / "phase5" / "training_runs.csv")
    g = runs.groupby("block").agg(runs=("seed", "size"), stable=("stable", "sum"))
    order = ["main", "p0", "p0sec", "pooled", "alt", "solo", "eqsteps"]
    ax = axes[2]
    ax.barh(range(len(order)), g.loc[order, "runs"], color=GRID, label="runs")
    ax.barh(range(len(order)), g.loc[order, "stable"], color=CAT[0], label="meet stability criterion")
    for i, b in enumerate(order):
        ax.text(g.loc[b, "runs"] + 1, i, f"{int(g.loc[b, 'stable'])}/{int(g.loc[b, 'runs'])}", va="center",
                fontsize=8, color=INK)
    ax.set_yticks(range(len(order)), order, fontsize=8)
    ax.invert_yaxis()
    ax.legend(frameon=False, fontsize=7, loc="lower right")
    style(ax, "c) Stable runs: 5 of 350")
    fig.suptitle("Fig. 7  A5 non-stationarity: policies keep changing at 8,000 episodes (churn above 5%, TD error still "
                 "high); results are 'after 8,000 episodes', not converged.", fontsize=9, x=0.01, ha="left")
    save(fig, "fig7_a5_nonstationarity.png")

    # ---------------- Fig 8: A8 association
    MED = pd.read_csv(ST / "a8_mediation.csv")
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
    ax = axes[0]
    d = SL[(SL.block == "main") & (SL.checkpoint == "final")]
    for level in LEVELS:
        dd = d[d.level == level]
        ax.scatter(dd.cr, dd.rf, color=LEVEL_C[level], s=36, edgecolor="#fcfcfb", linewidth=0.8, label=level)
    ax.set_xlabel("C5 cooperation rate (per seed)")
    ax.set_ylabel("Rescue fraction (per seed)")
    ax.legend(frameon=False, fontsize=8)
    style(ax, "a) Seeds with more cooperative actions rescue more, most\nclearly at Abundant (within-level Spearman 0.95)")
    ax = axes[1]
    single = MED[MED.model == "single"].reset_index(drop=True)
    joint = MED[(MED.model == "joint") & MED.term.isin(single.term)].set_index("term").loc[single.term].reset_index()
    y = np.arange(len(single))
    for k, (df, lab, c) in enumerate(((single, "one metric + level dummies", CAT[0]),
                                      (joint, "all six metrics + level dummies", CAT[1]))):
        ax.errorbar(df.coef, y + (k - 0.5) * 0.25, xerr=[df.coef - df.ci_lo, df.ci_hi - df.coef], fmt=MK[k],
                    color=c, capsize=3, label=lab)
    ax.axvline(0, color=MUTED, linewidth=1)
    ax.set_yticks(y, [names.get(t, t) for t in single.term], fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("Change in RF per 1 SD of the metric (95% cluster-bootstrap CI)")
    ax.legend(frameon=False, fontsize=7, loc="upper right", bbox_to_anchor=(1.0, 1.0))
    ax.set_xlim(-0.07, 0.17)
    style(ax, "b) A8 regression coefficients (ASSOCIATION, not causation)")
    fig.suptitle("Fig. 8  A8 (observational): with scarcity level held fixed, seeds with higher C5 cooperation rate and C4a "
                 "rescue more in one-metric models;\nin the joint model only C4a (which tracks reward, D22) has a CI "
                 "excluding zero (CR and C4a are collinear, VIF about 8).", fontsize=9, x=0.01, ha="left")
    save(fig, "fig8_a8_association.png")

    # ---------------- Fig 9: robustness of the scarcity trend
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    for k, (block, lab) in enumerate((("main", "Main (per-agent budgets)"), ("pooled", "Pooled team budget"),
                                      ("alt", "Alternate map 12×12, density 0.04"),
                                      ("p0", "All victims light (p_heavy = 0)"),
                                      ("p0sec", "All light, own calibration"))):
        M, m, ci = mean_ci(SL, block, "rf")
        errbar(ax, X + (k - 2) * 0.05, m, ci, CAT[k], MK[k], lab)
    level_axis(ax)
    ax.set_ylim(-0.02, 1.0)
    ax.set_ylabel("Rescue fraction (test)")
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    style(ax, "The decline with scarcity holds in every variant (Page two-sided p < 1e-10 in each)")
    fig.suptitle("Fig. 9  Robustness: learned rescue fraction by scarcity level across budget scope, map and victim mix "
                 "(mean ± 95% CI, 10 seeds each).", fontsize=9, x=0.01, ha="left")
    save(fig, "fig9_robustness.png")
    print("figures written:", sorted(p.name for p in FIG.glob("*.png")))


if __name__ == "__main__":
    main()
