"""Run the full calibration (spec §4) for every configuration in config/calibration.yaml and select the rho levels.

Uses ONLY the calibration seed range. Outputs (results/calibration/):
  <config>/time_to_90.csv, <config>/consumption.csv, <config>/sweep.csv, <config>/summary.json
  calibration_summary.json   all H, B_ref (empirical + analytic), sweep curves, selected levels, audit trail
Usage: python scripts/run_calibration.py [--instances N] [--workers W]   (defaults: from calibration.yaml, 2)
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tlr.calibration import (analytic_bref, calibration_instances, config_variant, pilot_sweep,  # noqa: E402
                             select_levels, step1_horizon, step2_bref)
from tlr.utils import load_config  # noqa: E402

OUT = ROOT / "results" / "calibration"


def calibrate_one(name: str, spec: dict, cal: dict, n_inst: int) -> dict:
    t0 = time.time()
    cfg = config_variant(load_config(), spec["grid_size"], spec["victim_density"], spec["p_heavy"])
    insts = calibration_instances(cfg, n_inst)
    s1 = step1_horizon(cfg, insts, cal)
    if s1["H"] is None:
        return {"name": name, "error": "T90 is infinite: the cooperative baseline did not reach 90% in >10% of instances"}
    s2 = step2_bref(cfg, insts, cal, s1["H"])
    an = analytic_bref(cfg, insts)
    policies = ["random", "greedy", "cooperative", "oracle"] if name == "main" else ["cooperative", "oracle"]
    rows = pilot_sweep(cfg, insts, s1["H"], s2["B_ref"], [float(r) for r in cal["rho_grid"]], policies)
    d = OUT / name
    d.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"instance": range(len(s1["T"])), "steps_to_90pct": s1["T"]}).to_csv(d / "time_to_90.csv", index=False)
    pd.DataFrame({"consumption": s2["consumption"]}).to_csv(d / "consumption.csv", index=False)
    df = pd.DataFrame(rows)
    df.to_csv(d / "sweep.csv", index=False)
    curves = {}
    for (rho, pol), g in df.groupby(["rho", "policy"]):
        curves.setdefault(pol, {})[float(rho)] = {
            "rf_mean": float(g.rf.mean()), "rescued_ge1": float((g.rescued >= 1).mean()),
            "exhausted": float((g.termination == "exhausted").mean()),
            "horizon": float((g.termination == "horizon").mean()),
            "all_rescued": float((g.termination == "all_rescued").mean()),
            "steps_mean": float(g.steps.mean()), "b0": int(g.b0.iloc[0])}
    feas = {float(r): float(g.drop_duplicates("instance").feasible.mean()) for r, g in df.groupby("rho")}
    summary = {"name": name, "spec": spec, "n_instances": n_inst, "H_max": s1["H_max"], "T90": s1["T90"],
               "H": s1["H"], "n_never_90pct": s1["n_never"], "B_ref": s2["B_ref"],
               "consumption_mean": s2["u_mean"], "consumption_median": s2["u_median"],
               "share_reaching_90pct_within_H": s2["share_reaching_90pct_within_H"],
               "rf_unlimited_within_H": s2["rf_unlimited"], "analytic": an, "curves": curves,
               "feasible_share": feas, "seconds": round(time.time() - t0, 1)}
    (d / "summary.json").write_text(json.dumps(summary, indent=2))
    return summary


def main() -> None:
    cal = yaml.safe_load((ROOT / "config" / "calibration.yaml").read_text())
    ap = argparse.ArgumentParser()
    ap.add_argument("--instances", type=int, default=int(cal["instances"]))
    ap.add_argument("--workers", type=int, default=2)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    confs = cal["configurations"]
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        futs = {name: ex.submit(calibrate_one, name, spec, cal, args.instances) for name, spec in confs.items()}
        res = {name: f.result() for name, f in futs.items()}
    for name, r in res.items():
        if "error" in r:
            print(f"[{name}] ERROR: {r['error']}")
            continue
        print(f"[{name}] H={r['H']} (T90={r['T90']}, never={r['n_never_90pct']}), B_ref={r['B_ref']} "
              f"(mean {r['consumption_mean']:.1f}, analytic {r['analytic']['B_ref_analytic']:.1f}), "
              f"reach90 within H={r['share_reaching_90pct_within_H']:.3f}, {r['seconds']} s")

    main = res["main"]
    coop = {r: v["rf_mean"] for r, v in main["curves"]["cooperative"].items()}
    orc = {r: v["rescued_ge1"] for r, v in main["curves"]["oracle"].items()}
    levels = select_levels(coop, orc, cal["selection"])
    print("selected levels:", {k: levels[k] for k in ("abundant", "moderate", "scarce", "critical")})
    for line in levels["trail"]:
        print("  ", line)

    # Stability: the same rules applied to every other configuration's own curve (descriptive only).
    stability = {}
    for name, r in res.items():
        if "error" in r:
            continue
        c = {x: v["rf_mean"] for x, v in r["curves"]["cooperative"].items()}
        o = {x: v["rescued_ge1"] for x, v in r["curves"]["oracle"].items()}
        stability[name] = {k: v for k, v in select_levels(c, o, cal["selection"]).items() if k != "trail"}

    # Alternate configuration decision (pre-stated rule).
    crit = levels["critical"]
    alt = cal["alternate_configuration"]["default"]
    alt_feas = res[alt]["curves"]["oracle"][crit]["rescued_ge1"]
    if alt_feas < float(cal["selection"]["critical_min_oracle_feasible"]):
        alt = cal["alternate_configuration"]["fallback"]
    summary = {"levels": levels, "stability_by_configuration": stability, "alternate_configuration": alt,
               "alternate_default_oracle_feasible_at_critical": alt_feas, "configurations": res}
    (OUT / "calibration_summary.json").write_text(json.dumps(summary, indent=2, default=float))
    print("alternate configuration:", alt, f"(default's oracle>=1 share at Critical = {alt_feas:.3f})")


if __name__ == "__main__":
    main()
