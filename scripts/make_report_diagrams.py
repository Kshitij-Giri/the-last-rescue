"""Report diagrams (Section 4): an example environment instance and the per-step transition pipeline.

fig0a_environment.png : frozen TEST instance 0 of the main configuration (seed from instance_sets.json), with base, walls,
                        hazard cells, light/heavy victims, three agents at the base, and the radius-1 / radius-2 / radius-3
                        footprints of passive sensing, SEARCH and teammate visibility.
fig0b_step_pipeline.png: the order of operations inside one simultaneous step (spec §1.3).
Usage: python scripts/make_report_diagrams.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Rectangle  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from tlr.mapgen import HAZARD, WALL, generate_instance  # noqa: E402
from tlr.utils import load_config  # noqa: E402

FIG = ROOT / "results" / "figures"
INK, MUTED = "#0b0b0b", "#52514e"


def environment() -> None:
    seed = json.loads((ROOT / "results" / "calibration" / "instance_sets.json").read_text())["main"]["test"]["seeds"][0]
    inst = generate_instance(load_config(), seed)
    L = inst.L
    fig, ax = plt.subplots(figsize=(6.6, 6.2))
    for k in range(L * L):
        r, c = divmod(k, L)
        g = inst.grid[k]
        face = "#3d3d3a" if g == WALL else ("#f6d38a" if g == HAZARD else "#fcfcfb")
        ax.add_patch(Rectangle((c, r), 1, 1, facecolor=face, edgecolor="#d9d8d4", linewidth=0.8))
    br, bc = divmod(inst.base, L)
    for rad, col, lab in ((3, "#6250d6", "teammates visible (r = 3)"), (2, "#1baf7a", "SEARCH footprint (r = 2)"),
                          (1, "#2a78d6", "passive sensing (r = 1)")):
        r0, c0 = max(0, br - rad), max(0, bc - rad)
        r1, c1 = min(L, br + rad + 1), min(L, bc + rad + 1)
        ax.add_patch(Rectangle((c0, r0), c1 - c0, r1 - r0, fill=False, edgecolor=col, linewidth=2.2,
                               linestyle="--", label=lab))
    ax.add_patch(Rectangle((bc, br), 1, 1, facecolor="#cde2fb", edgecolor=INK, linewidth=1.5))
    ax.text(bc + 0.5, br + 0.32, "BASE", ha="center", va="center", fontsize=6.5, color=INK, fontweight="bold")
    ax.text(bc + 0.5, br + 0.72, "1 2 3", ha="center", va="center", fontsize=7, color=INK)
    for vid, cell in enumerate(inst.victim_cells):
        r, c = divmod(int(cell), L)
        heavy = bool(inst.victim_heavy[vid])
        ax.scatter(c + 0.5, r + 0.5, s=180, marker="s" if heavy else "o",
                   color="#eb6834" if heavy else "#e87ba4", edgecolor=INK, linewidth=0.8, zorder=3)
        ax.text(c + 0.5, r + 0.5, "H" if heavy else "L", ha="center", va="center", fontsize=7, color="#fcfcfb",
                fontweight="bold", zorder=4)
    ax.set_xlim(0, L)
    ax.set_ylim(L, 0)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    from matplotlib.lines import Line2D
    extra = [Rectangle((0, 0), 1, 1, facecolor="#3d3d3a", label="wall"),
             Rectangle((0, 0), 1, 1, facecolor="#f6d38a", edgecolor="#d9d8d4", label="hazard (entry costs 2)"),
             Line2D([], [], marker="o", color="w", markerfacecolor="#e87ba4", markeredgecolor=INK, markersize=10,
                    label="LIGHT victim (one RESCUE)"),
             Line2D([], [], marker="s", color="w", markerfacecolor="#eb6834", markeredgecolor=INK, markersize=10,
                    label="HEAVY victim (RESCUE + ASSIST, same step)")]
    h, lab = ax.get_legend_handles_labels()
    ax.legend(handles=extra + h, loc="upper left", bbox_to_anchor=(1.01, 1.0), frameon=False, fontsize=8)
    ax.set_title(f"Example instance (frozen test instance 0, seed {seed}): 10 x 10 grid, 6 victims (3 heavy)",
                 fontsize=9, loc="left")
    fig.tight_layout()
    fig.savefig(FIG / "fig0a_environment.png", dpi=170, bbox_inches="tight")
    plt.close(fig)


def pipeline() -> None:
    steps = [("1  Observe", "each agent builds o_t from its own\nmemory, own cell, teammates\nwithin r = 3 and own budget"),
             ("2  Mask", "valid actions from the agent's\nown view; WAIT is always valid"),
             ("3  Choose", "all n agents choose at the same\ntime (policy or epsilon-greedy)"),
             ("4  Pay", "budgets debited (pooled: rotating\npriority; unpaid action -> WAIT)"),
             ("5  Move", "moving agents change cell\n(cells may be shared)"),
             ("6  Resolve", "LIGHT: any RESCUE. HEAVY:\nRESCUE + ASSIST by different\nagents, same cell, same step"),
             ("7  Sense", "radius-1 view (+ radius-2 after\nSEARCH) overwrites memory\nwith the truth"),
             ("8  Reward", "R_i = λI·r_ind + λT·r_team\n − λC·cost_i"),
             ("9  Terminate?", "all rescued / no agent can\nafford RESCUE / t = H")]
    fig, ax = plt.subplots(figsize=(11, 4.6))
    ax.axis("off")
    w, h, gx, gy = 2.0, 0.95, 0.35, 0.6
    pos = [(k * (w + gx), gy + h) for k in range(5)] + [((3 - k) * (w + gx) + (w + gx) / 2, 0) for k in range(4)]
    pos = [(k * (w + gx), gy + h) for k in range(5)] + [((4 - j) * (w + gx), 0) for j in range(4)]
    for k, ((t, d), (x, y)) in enumerate(zip(steps, pos)):
        face = "#cde2fb" if k < 3 else ("#fde2d5" if k < 7 else "#d6f2e6")
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                                    facecolor=face, edgecolor="#256abf", linewidth=1.2))
        ax.text(x + 0.1, y + h - 0.2, t, ha="left", va="center", fontsize=9.5, fontweight="bold", color=INK)
        ax.text(x + 0.1, y + h - 0.42, d, ha="left", va="top", fontsize=7.2, color=INK, linespacing=1.25)
    arrow = dict(arrowstyle="->", color=MUTED, lw=1.4)
    for k in range(4):
        x, y = pos[k]
        ax.annotate("", xy=(x + w + gx, y + h / 2), xytext=(x + w, y + h / 2), arrowprops=arrow)
    x4, y4 = pos[4]
    ax.annotate("", xy=(x4 + w / 2, h), xytext=(x4 + w / 2, y4), arrowprops=arrow)
    for k in range(5, 8):
        x, y = pos[k]
        ax.annotate("", xy=(x - gx, y + h / 2), xytext=(x, y + h / 2), arrowprops=arrow)
    xl, yl = pos[8]
    ax.annotate("next step t+1 (if not terminated)", xy=(pos[0][0] + w / 2, pos[0][1]), xytext=(xl + w / 2 - 0.4, yl + h + 0.05),
                fontsize=7.5, color=MUTED, ha="center",
                arrowprops=dict(arrowstyle="->", color=MUTED, lw=1.0, linestyle="--", connectionstyle="arc3,rad=-0.25"))
    ax.text(0, 2 * h + gy + 0.22, "Blue: agent side (uses only the agent's own information)   "
            "Orange: environment side (ground truth)   Green: feedback and termination", fontsize=8.5, color=INK)
    ax.set_xlim(-0.1, 5 * (w + gx))
    ax.set_ylim(-0.15, 2 * h + gy + 0.45)
    fig.tight_layout()
    fig.savefig(FIG / "fig0b_step_pipeline.png", dpi=170, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    environment()
    pipeline()
    print("written fig0a_environment.png, fig0b_step_pipeline.png")
