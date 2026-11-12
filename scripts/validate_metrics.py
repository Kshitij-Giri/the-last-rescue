"""Phase 2 construct-validity check for the cooperation metrics (spec §3 "Construct validity plan").

NOT AN EXPERIMENTAL RESULT. Budgets and horizon here are uncalibrated placeholders (calibration is Phase 3), and no
learned policy is involved. The purpose is only to check that the metrics behave as intended on policies whose
behaviour we know by design:

Expectations (written before running; the script reports PASS/FAIL honestly):
  X1 cooperative > random and cooperative > greedy on C1 EAR, C3 TDI and C5 CR (pooled means);
  X2 cooperative < random and cooperative < greedy on C2 RSR_other;
  X3 greedy has C5 CR = 0 and completes no heavy rescue (it never ASSISTs);
  X4 no cooperation metric is identical to collective return: |Spearman rho| < 0.95 across episodes.
Also reported (descriptive): oracle reference rows (full information, centralized - NOT comparable as a policy),
and the oracle-vs-exhaustive gap on tiny instances.

Usage: python scripts/validate_metrics.py [--instances 50]
Outputs: results/phase2/metric_validation_episodes.csv, results/phase2/metric_validation_summary.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tlr.baselines import make_team  # noqa: E402
from tlr.costs import CostModel  # noqa: E402
from tlr.env import RescueEnv  # noqa: E402
from tlr.evaluate import run_episode  # noqa: E402
from tlr.mapgen import compute_statics, generate_instance  # noqa: E402
from tlr.metrics import episode_record  # noqa: E402
from tlr.oracle import OraclePolicy, exhaustive_plan_count, greedy_insertion_plan  # noqa: E402
from tlr.utils import deep_update, instance_seed, load_config  # noqa: E402

PLACEHOLDER_H = 200
PLACEHOLDER_B0 = {"unlimited": 10_000, "b0=40": 40, "b0=20": 20}
POLICIES = ["random", "greedy", "cooperative", "oracle"]
METRICS = ["rf", "ear", "rsr", "rsr_other", "tdi", "pss", "gini_consumption", "cr"]


def pooled(df: pd.DataFrame, num: str, den: str) -> float:
    d = df[den].sum()
    return float(df[num].sum() / d) if d else float("nan")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--instances", type=int, default=50)
    args = ap.parse_args()
    cfg = load_config()
    cm = CostModel.from_config(cfg)
    rows = []
    for k in range(args.instances):
        inst = generate_instance(cfg, instance_seed("validation", k))
        st = compute_statics(inst, cm, [1, 2])
        for blabel, b0 in PLACEHOLDER_B0.items():
            env = RescueEnv(cfg, horizon=PLACEHOLDER_H, b_ref=40)
            for name in POLICIES:
                pol = OraclePolicy() if name == "oracle" else make_team(name)
                log = run_episode(env, inst, b0, pol, statics=st, seed=k)
                rows.append(episode_record(inst, st, log, cm, 1, policy=name, budget=blabel, instance=k))
    df = pd.DataFrame(rows)
    out = ROOT / "results" / "phase2"
    out.mkdir(parents=True, exist_ok=True)
    df.to_csv(out / "metric_validation_episodes.csv", index=False)

    lines = ["# Phase 2 metric construct-validity check", "",
             "**Not an experimental result.** Uncalibrated placeholder budgets (b0) and horizon H = "
             f"{PLACEHOLDER_H}; {args.instances} validation instances; deterministic baselines; ratio metrics pooled "
             "over episodes (sum of numerators / sum of denominators). The oracle is a full-information centralized "
             "REFERENCE, shown for context only.", ""]
    summary = []
    for (blabel, name), g in df.groupby(["budget", "policy"], sort=False):
        summary.append({"budget": blabel, "policy": name, "episodes": len(g),
                        "rf": g["rf"].mean(), "heavy_rescued": g["rescued_heavy"].sum(),
                        "ear": pooled(g, "ear_num", "ear_den"),
                        "rsr": pooled(g.assign(x=g.rsr_other_num + g.rsr_self_num), "x", "rsr_den"),
                        "rsr_other": pooled(g, "rsr_other_num", "rsr_den"),
                        "tdi": g["tdi"].mean(), "pss": pooled(g, "pss_num", "pss_den"),
                        "gini_consumption": g["gini_consumption"].mean(), "cr": pooled(g, "cr_num", "cr_den"),
                        "collective_return": g["collective_return"].mean()})
    S = pd.DataFrame(summary)
    S.to_csv(out / "metric_validation_summary.csv", index=False)
    lines.append(S.to_markdown(index=False, floatfmt=".3f"))
    lines.append("")

    checks = []
    for blabel in PLACEHOLDER_B0:
        s = S[S.budget == blabel].set_index("policy")
        co, ra, gr = s.loc["cooperative"], s.loc["random"], s.loc["greedy"]
        for m in ("ear", "tdi", "cr"):
            for other, nm in ((ra, "random"), (gr, "greedy")):
                a, b = co[m], other[m]
                ok = bool(np.isnan(b) or a > b) if not np.isnan(a) else False
                checks.append(("X1", blabel, f"cooperative {m} {a:.3f} > {nm} {b:.3f}"
                               + (" (other undefined: no ASSIST at all)" if np.isnan(b) else ""), ok))
        for other, nm in ((ra, "random"), (gr, "greedy")):
            a, b = co["rsr_other"], other["rsr_other"]
            checks.append(("X2", blabel, f"cooperative rsr_other {a:.3f} < {nm} {b:.3f}", bool(a < b)))
        checks.append(("X3", blabel, f"greedy cr = {gr['cr']:.3f}, heavy rescued = {int(gr['heavy_rescued'])}",
                       bool(gr["cr"] == 0 and gr["heavy_rescued"] == 0)))
        dec = df[(df.budget == blabel) & (df.policy != "oracle")]
        for m in ("ear", "rsr_other", "tdi", "pss", "gini_consumption", "cr"):
            sub = dec[["collective_return", m]].dropna()
            rho = spearmanr(sub["collective_return"], sub[m]).statistic if len(sub) > 2 else float("nan")
            checks.append(("X4", blabel, f"Spearman(collective_return, {m}) = {rho:.3f} (n = {len(sub)})",
                           bool(np.isnan(rho) or abs(rho) < 0.95)))
    lines += ["## Pre-stated checks", "", "| check | budget | detail | result |", "|---|---|---|---|"]
    lines += [f"| {c} | {b} | {d} | {'PASS' if ok else 'FAIL'} |" for c, b, d, ok in checks]
    n_fail = sum(1 for *_, ok in checks if not ok)
    lines += ["", f"**{len(checks) - n_fail}/{len(checks)} checks passed.**", ""]

    # Oracle vs exhaustive macro-plan optimum on tiny instances (descriptive quality of the oracle reference).
    small = deep_update(cfg, {"env": {"grid_size": 6, "victim_density": 0.09}})
    cms = CostModel.from_config(small)
    gaps, opt_tot, g_tot = [], 0, 0
    for k in range(100):
        inst = generate_instance(small, instance_seed("calibration", k))
        st = compute_statics(inst, cms, [1, 2])
        for b0 in (5, 8, 12):
            g = len(greedy_insertion_plan(inst, st, cms, 3, 40, [b0] * 3, pooled=False))
            o = exhaustive_plan_count(inst, st, cms, 3, 40, [b0] * 3, pooled=False)
            gaps.append(o - g)
            opt_tot += o
            g_tot += g
    gaps = np.array(gaps)
    lines += ["## Oracle reference vs exhaustive macro-plan optimum (tiny instances: 6x6, V = 3, b0 in {5, 8, 12})", "",
              f"{len(gaps)} cases; oracle equals the optimum in {int((gaps == 0).sum())} "
              f"({100 * np.mean(gaps == 0):.1f}%); total rescues oracle {g_tot} vs optimum {opt_tot} "
              f"({100 * g_tot / opt_tot:.1f}%); max gap {int(gaps.max())}.", ""]
    text = "\n".join(lines)
    (out / "metric_validation_summary.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
