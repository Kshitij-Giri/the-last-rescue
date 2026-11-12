"""Analyse a pilot variant exactly as docs/pilot_protocol.md specifies (gate, episode-count rule, joint-rescue reading).

Usage: python scripts/analyze_pilot.py P0 [P0x2 ...]
Outputs: results/pilot/<variant>/analysis.json, results/pilot/<variant>/seed_table.md,
         results/pilot/figures/fig_pilot_<variant>.png
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import wilcoxon  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PIL = ROOT / "results" / "pilot"
COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
MARKERS = ["o", "s", "^", "D", "v"]
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"


def style(ax) -> None:
    ax.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(colors=MUTED)


def analyze(variant: str) -> dict:
    base = json.loads((PIL / "baselines_validation_abundant.json").read_text())
    rand = base["random"]["rf"]
    seeds = sorted(p for p in PIL.glob(f"{variant}/seed_*") if p.is_dir())
    cks = {p.name: pd.read_csv(p / "checkpoints.csv") for p in seeds}
    runs = {p.name: json.loads((p / "run.json").read_text()) for p in seeds}
    rows = []
    for name, ck in cks.items():
        f = ck.iloc[-1]
        rows.append({"seed": name.split("_")[1], "val_rf": f.rf, "heavy_share": f.rescued_heavy_share,
                     "light_share": f.rescued_light_share, "assist_actions_per_ep": f.assist_actions / 50,
                     "ear": f.ear, "cr": f.cr, "e1_per_ep": f.e1_abandonment, "failed_rescue_per_ep": f.failed_rescue,
                     "tdi": f.tdi, "rsr_other": f.rsr_other, "steps": f.steps, "exhausted": f.exhausted,
                     "horizon_end": f.horizon, "best_val_rf": runs[name]["best_val_rf"],
                     "best_val_episode": runs[name]["best_val_episode"], "last_churn": runs[name]["last_churn"],
                     "last3_rf_range": runs[name]["last3_rf_range"], "stable": runs[name]["stable"],
                     "seconds": runs[name]["seconds"], "env_steps": runs[name]["total_env_steps"]})
    T = pd.DataFrame(rows)
    (PIL / variant / "seed_table.md").write_text(T.to_markdown(index=False, floatfmt=".3f"))
    d = T.val_rf.values - rand
    above, below = int((d > 0).sum()), int((d < 0).sum())
    p = float(wilcoxon(d, alternative="greater").pvalue) if np.any(d != 0) else 1.0
    delta = (above - below) / len(d)
    gate = bool(p < 0.05 and delta >= 0.33)
    # episode-count rule: mean validation RF at 75% vs 100% of training
    E = int(cks[next(iter(cks))].episode.max())
    def at(frac):
        return float(np.mean([ck.loc[(ck.episode - frac * E).abs().idxmin(), "rf"] for ck in cks.values()]))
    rise = at(1.0) - at(0.75)
    hs = T.heavy_share.values
    if (hs >= 0.10).sum() >= 3:
        joint = "learned joint rescue (heavy share >= 0.10 in >= 3/5 seeds)"
    elif (hs < 0.02).sum() >= 3:
        joint = "NOT learned (heavy share < 0.02 in >= 3/5 seeds)"
    else:
        joint = "partially / unreliably learned"
    out = {"variant": variant, "random_val_rf": rand, "iql_val_rf_mean": float(T.val_rf.mean()),
           "seeds_above_random": above, "seeds_below_random": below, "wilcoxon_one_sided_p": p, "delta_1": delta,
           "gate_passed": gate, "episodes": E, "rf_at_75pct": at(0.75), "rf_at_100pct": at(1.0),
           "rise_last_quarter": rise, "still_learning": bool(rise > 0.02), "joint_rescue_reading": joint,
           "heavy_share_by_seed": hs.tolist(), "stable_runs": int(T.stable.sum()), "n_runs": len(T),
           "mean_seconds": float(T.seconds.mean()), "mean_env_steps": float(T.env_steps.mean())}
    (PIL / variant / "analysis.json").write_text(json.dumps(out, indent=1))

    # Figure: validation RF, heavy-victim share, churn and |TD| per checkpoint, one line per seed (4 small multiples).
    fig, axes = plt.subplots(2, 2, figsize=(11, 7.5), sharex=True)
    panels = [("rf", "Validation rescue fraction (greedy policy)"), ("rescued_heavy_share", "Share of heavy victims rescued"),
              ("churn", "Policy churn vs previous checkpoint"), ("train_mean_abs_td", "Mean |TD error| (last 500 episodes)")]
    for ax, (col, title) in zip(axes.flat, panels):
        for j, (name, ck) in enumerate(cks.items()):
            ax.plot(ck.episode, ck[col], color=COLORS[j], marker=MARKERS[j], markersize=4, linewidth=1.6,
                    label=f"seed {name.split('_')[1]}")
        if col == "rf":
            for nm, ls in (("random", ":"), ("greedy", "--"), ("cooperative", "-.")):
                ax.axhline(base[nm]["rf"], color=MUTED, linestyle=ls, linewidth=1)
                ax.text(E, base[nm]["rf"], f" {nm} {base[nm]['rf']:.2f}", fontsize=7, color=INK, va="center")
            ax.set_ylim(-0.02, 1.05)
        if col == "rescued_heavy_share":
            ax.axhline(base["cooperative"]["rescued_heavy_share"], color=MUTED, linestyle="-.", linewidth=1)
            ax.set_ylim(-0.02, 1.05)
        if col == "churn":
            ax.axhline(0.05, color=MUTED, linestyle="--", linewidth=1)
            ax.text(0, 0.05, " 5% stability threshold", fontsize=7, color=INK, va="bottom")
        ax.set_title(title, fontsize=9, loc="left")
        style(ax)
    for ax in axes[1]:
        ax.set_xlabel("training episodes")
    axes[0, 0].legend(frameon=False, fontsize=7, loc="upper left")
    fig.suptitle(f"Pilot {variant} at Abundant (b0 = 64), 5 pilot seeds, 50 validation instances. Gate "
                 f"{'PASSED' if gate else 'FAILED'}: IQL RF {T.val_rf.mean():.3f} vs random {rand:.3f}; "
                 f"joint rescue: {joint.split(' (')[0]}", fontsize=10, x=0.01, ha="left")
    fig.tight_layout()
    (PIL / "figures").mkdir(parents=True, exist_ok=True)
    fig.savefig(PIL / "figures" / f"fig_pilot_{variant}.png", dpi=150)
    plt.close(fig)
    return out


if __name__ == "__main__":
    for v in sys.argv[1:]:
        print(json.dumps(analyze(v), indent=1))
        print((PIL / v / "seed_table.md").read_text())
