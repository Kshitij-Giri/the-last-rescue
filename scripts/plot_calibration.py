"""Calibration figures and tables from results/calibration/*.json (spec §4). Re-runnable from saved files only.

Figures (results/calibration/figures/):
  fig_cal_main.png         RF vs rho (Abundant -> Critical) for cooperative, oracle reference, greedy, random; selected
                           levels marked; oracle-feasible share on a second panel (not a second axis).
  fig_cal_sensitivity.png  cooperative-baseline RF vs rho for every configuration (does rho keep its meaning?)
  fig_cal_consumption.png  per-agent consumption with unlimited budget (main) and the B_ref quantile
Tables (results/calibration/):
  table_bref.csv / .md     H, T90, B_ref (empirical q90), mean consumption, analytic estimate, ratios
  table_sweep_main.csv/.md the main configuration's sweep at every rho
  table_sensitivity.csv/.md cooperative RF per rho per configuration, and the spread across configurations
Usage: python scripts/plot_calibration.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CAL = ROOT / "results" / "calibration"
FIG = CAL / "figures"
# Validated categorical palette (dataviz reference instance, light mode); contrast WARN for slots 3-5 is relieved by
# distinct markers + direct labels + the tables written next to every figure.
COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#6250d6"]
MARKERS = ["o", "s", "^", "D", "v", "P"]
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"


def style(ax) -> None:
    ax.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(MUTED)
    ax.tick_params(colors=MUTED)


def main() -> None:
    S = json.loads((CAL / "calibration_summary.json").read_text())
    conf, lv = S["configurations"], S["levels"]
    FIG.mkdir(parents=True, exist_ok=True)
    levels = {"Abundant": lv["abundant"], "Moderate": lv["moderate"], "Scarce": lv["scarce"],
              "Critical": lv["critical"]}

    # ---- Table: B_ref and H per configuration
    rows = []
    for name, r in conf.items():
        a = r["analytic"]["B_ref_analytic"]
        rows.append({"configuration": name, "L": r["spec"]["grid_size"], "density": r["spec"]["victim_density"],
                     "p_heavy": r["spec"]["p_heavy"], "V_mean": r["analytic"]["V"], "free_cells": r["analytic"]["A_free"],
                     "T90": r["T90"], "H": r["H"], "never_90pct_in_Hmax": r["n_never_90pct"],
                     "reach_90pct_within_H": r["share_reaching_90pct_within_H"],
                     "B_ref_empirical_q90": r["B_ref"], "consumption_mean": r["consumption_mean"],
                     "B_ref_analytic": a, "analytic_over_mean": a / r["consumption_mean"],
                     "analytic_over_q90": a / r["B_ref"]})
    T = pd.DataFrame(rows)
    T.to_csv(CAL / "table_bref.csv", index=False)
    (CAL / "table_bref.md").write_text(T.to_markdown(index=False, floatfmt=".3f"))

    # ---- Table: main sweep
    m = conf["main"]
    rhos = sorted((float(x) for x in m["curves"]["cooperative"]), reverse=True)
    sw = []
    for r in rhos:
        k = str(r) if str(r) in m["curves"]["cooperative"] else repr(r)
        c = m["curves"]
        sw.append({"rho": r, "b0": c["cooperative"][k]["b0"],
                   **{f"rf_{p}": c[p][k]["rf_mean"] for p in ("cooperative", "oracle", "greedy", "random")},
                   "oracle_rescues_ge1": c["oracle"][k]["rescued_ge1"], "feasible_share": m["feasible_share"][k],
                   "coop_exhausted": c["cooperative"][k]["exhausted"], "coop_horizon": c["cooperative"][k]["horizon"],
                   "coop_all_rescued": c["cooperative"][k]["all_rescued"],
                   "coop_steps_mean": c["cooperative"][k]["steps_mean"],
                   "selected_as": next((n for n, v in levels.items() if abs(v - r) < 1e-9), "")})
    SW = pd.DataFrame(sw)
    SW.to_csv(CAL / "table_sweep_main.csv", index=False)
    (CAL / "table_sweep_main.md").write_text(SW.to_markdown(index=False, floatfmt=".3f"))

    # ---- Figure 1: main calibration (two panels, shared x; NOT a dual axis)
    fig, (ax, ax2) = plt.subplots(2, 1, figsize=(8, 7), sharex=True, gridspec_kw={"height_ratios": [3, 1.2]})
    series = [("cooperative", "Cooperative baseline"), ("oracle", "Oracle reference (full information)"),
              ("greedy", "Greedy baseline"), ("random", "Random baseline")]
    for j, (key, lab) in enumerate(series):
        y = SW[f"rf_{key}"]
        ax.plot(SW.rho, y, color=COLORS[j], marker=MARKERS[j], markersize=7, linewidth=2, label=lab)
    # Identity: legend + distinct marker shapes (direct labels collided where curves converge); exact values are in
    # table_sweep_main.md next to the figure.
    for name, v in levels.items():
        ax.axvline(v, color=MUTED, linewidth=0.8, linestyle=":")
        ax.text(v, 1.04, name, ha="center", fontsize=8, color=INK)
    for tgt in (0.70, 0.40):
        ax.axhline(tgt, color=GRID, linewidth=1.2, linestyle="--")
    ax.axhspan(0.10, 0.15, color=GRID, alpha=0.6, linewidth=0)
    ax.set_ylabel("Rescue fraction (mean over 200 calibration instances)")
    ax.set_ylim(-0.02, 1.1)
    ax.legend(loc="center left", bbox_to_anchor=(0.0, 0.66), frameon=False, fontsize=8)
    ax.set_title("Calibration sweep, main configuration (L = 10, density 0.06, H = %d, B_ref = %d)\n"
                 "Selected levels give cooperative RF 0.97 / 0.70 / 0.39 / 0.22. Critical sits above the 0.10-0.15 band\n"
                 "(shaded) because rho = 0.1 is solvable in only 33%% of instances. Dashed lines: 0.70 and 0.40 targets."
                 % (m["H"], m["B_ref"]), fontsize=9, loc="left")
    ax2.plot(SW.rho, SW.oracle_rescues_ge1, color=COLORS[1], marker=MARKERS[1], linewidth=2)
    ax2.axhline(0.95, color=MUTED, linestyle="--", linewidth=1)
    ax2.text(0.98, 0.5, "dashed: 95% feasibility requirement at Critical", fontsize=8, color=INK, va="center")
    ax2.set_ylabel("Share solvable\n(oracle rescues >= 1)", fontsize=8)
    ax2.set_xlabel("rho = initial per-agent budget / B_ref   (Abundant -> Critical)")
    ax2.set_ylim(0, 1.08)
    ax2.invert_xaxis()
    for a in (ax, ax2):
        style(a)
    fig.tight_layout()
    fig.savefig(FIG / "fig_cal_main.png", dpi=150)
    plt.close(fig)

    # ---- Figure 2 + table: sensitivity of RF_coop(rho) across configurations
    names = list(conf)
    sens = pd.DataFrame({"rho": rhos})
    for name in names:
        cc = conf[name]["curves"]["cooperative"]
        sens[name] = [cc[str(r) if str(r) in cc else repr(r)]["rf_mean"] for r in rhos]
    main_like = [n for n in names if n != "main_p0"]
    sens["spread_p05_configs"] = sens[main_like].max(axis=1) - sens[main_like].min(axis=1)
    sens.to_csv(CAL / "table_sensitivity.csv", index=False)
    (CAL / "table_sensitivity.md").write_text(sens.to_markdown(index=False, floatfmt=".3f"))
    fig, ax = plt.subplots(figsize=(8, 5))
    for j, name in enumerate(names):
        r = conf[name]
        lab = f"{name}: L={r['spec']['grid_size']}, d={r['spec']['victim_density']}, p_heavy={r['spec']['p_heavy']}, B_ref={r['B_ref']}"
        ax.plot(sens.rho, sens[name], color=COLORS[j % 6], marker=MARKERS[j % 6], linewidth=2, markersize=6,
                label=lab, linestyle="--" if name == "main_p0" else "-")
    for name, v in levels.items():
        ax.axvline(v, color=MUTED, linewidth=0.8, linestyle=":")
        ax.text(v, 1.04, name, ha="center", fontsize=8, color=INK)
    ax.invert_xaxis()
    ax.set_ylim(-0.02, 1.1)
    ax.set_xlabel("rho (each configuration uses its own calibrated B_ref and H)   (Abundant -> Critical)")
    ax.set_ylabel("Cooperative-baseline rescue fraction")
    ax.set_title("Does rho mean the same thing across map sizes and densities?\nClose at high rho "
                 "(spread <= %.2f for rho >= 0.7); diverges at low rho (spread %.2f at rho = 0.5, %.2f at 0.2)"
                 % (sens.loc[sens.rho >= 0.7 - 1e-9, "spread_p05_configs"].max(),
                    float(sens.loc[np.isclose(sens.rho, 0.5), "spread_p05_configs"].iloc[0]),
                    float(sens.loc[np.isclose(sens.rho, 0.2), "spread_p05_configs"].iloc[0])), fontsize=9, loc="left")
    ax.legend(frameon=False, fontsize=7, loc="lower left")
    style(ax)
    fig.tight_layout()
    fig.savefig(FIG / "fig_cal_sensitivity.png", dpi=150)
    plt.close(fig)

    # ---- Figure 3: consumption distribution (main)
    u = pd.read_csv(CAL / "main" / "consumption.csv")["consumption"]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(u, bins=range(0, int(u.max()) + 5, 4), color=COLORS[0], edgecolor="#fcfcfb", linewidth=2)
    ax.axvline(m["B_ref"], color=INK, linewidth=1.5)
    ax.text(m["B_ref"] + 1, ax.get_ylim()[1] * 0.9, f"B_ref = 90th percentile = {m['B_ref']}", fontsize=8, color=INK)
    ax.axvline(m["consumption_mean"], color=MUTED, linewidth=1, linestyle="--")
    ax.text(m["consumption_mean"] + 1, ax.get_ylim()[1] * 0.75, f"mean = {m['consumption_mean']:.1f}", fontsize=8,
            color=INK)
    ax.axvline(m["analytic"]["B_ref_analytic"], color=COLORS[1], linewidth=1.5, linestyle="-.")
    ax.text(m["analytic"]["B_ref_analytic"] + 1, ax.get_ylim()[1] * 0.6,
            f"analytic estimate = {m['analytic']['B_ref_analytic']:.1f}", fontsize=8, color=INK)
    ax.set_xlabel("Resource units consumed per agent (cooperative baseline, unlimited budget, H = %d)" % m["H"])
    ax.set_ylabel("Agents (3 per instance x 200 instances)")
    ax.set_title("B_ref is the budget that suffices for 90% of agents; the analytic formula captures about half "
                 "of the mean need", fontsize=9, loc="left")
    style(ax)
    fig.tight_layout()
    fig.savefig(FIG / "fig_cal_consumption.png", dpi=150)
    plt.close(fig)
    print(T.to_string(index=False))
    print()
    print(sens.to_string(index=False))


if __name__ == "__main__":
    main()
