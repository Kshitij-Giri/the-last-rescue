"""Calibration of the horizon H, the reference budget B_ref and the scarcity levels rho (spec §4, review point 3).

Procedure (all parameters and selection rules in config/calibration.yaml, hashed before any run):
  Step 1  H     = ceil(T90 / slack), T90 = 90th percentile over calibration instances of the step at which the cooperative
                 baseline (unlimited budget, cap H_max = 40 L) has rescued >= ceil(0.9 V) victims.
  Step 2  B_ref = 90th percentile of per-agent resource consumption of the cooperative baseline (unlimited budget, horizon
                 H), pooled over agents and instances -> rho = 1 means "just enough" in ~90% of cases.
  Step 3  analytic back-of-envelope B_ref for comparison.
  Step 4  pilot sweep over rho with the cooperative baseline and the oracle reference -> four levels by pre-stated rules.
Only the "calibration" seed range is used; the RL agents are never involved (avoids circularity).
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from .baselines import make_team
from .costs import CostModel
from .env import RescueEnv
from .evaluate import run_episode
from .mapgen import Instance, MapStatics, compute_statics, feasible_victims, generate_instance
from .oracle import OraclePolicy
from .utils import deep_update, initial_budget, instance_seed, round_half_up


def config_variant(cfg: dict[str, Any], grid_size: int, victim_density: float, p_heavy: float) -> dict[str, Any]:
    """The default config with a different map size, victim density and heavy share."""
    return deep_update(cfg, {"env": {"grid_size": grid_size, "victim_density": victim_density, "p_heavy": p_heavy}})


def calibration_instances(cfg: dict[str, Any], n: int) -> list[tuple[Instance, MapStatics]]:
    """Instances 0..n-1 of the calibration split, with their static tables."""
    cm = CostModel.from_config(cfg)
    r = [int(cfg["env"]["radius_passive"]), int(cfg["env"]["radius_search"])]
    out = []
    for k in range(n):
        inst = generate_instance(cfg, instance_seed("calibration", k))
        out.append((inst, compute_statics(inst, cm, r)))
    return out


def quantile(x: np.ndarray, q: float, method: str) -> float:
    return float(np.quantile(np.asarray(x, dtype=float), q, method=method))


def _time_to_fraction(log, V: int, frac: float) -> float:
    """Number of steps until >= ceil(frac * V) victims were rescued (inf if never)."""
    need = math.ceil(frac * V - 1e-9)
    times = sorted(e["t"] + 1 for e in log.events if e["type"] == "rescue")  # rescue in step t is done after t+1 steps
    return float(times[need - 1]) if len(times) >= need else math.inf


def step1_horizon(cfg: dict[str, Any], insts, cal: dict[str, Any]) -> dict[str, Any]:
    """Step 1: horizon from the cooperative baseline's time-to-90%-rescue with unlimited budget."""
    L = int(cfg["env"]["grid_size"])
    H_max = int(cal["h_max_factor"]) * L
    env = RescueEnv(cfg, horizon=H_max, b_ref=1)  # b_ref only affects f4, which baselines do not use
    T = []
    for k, (inst, st) in enumerate(insts):
        log = run_episode(env, inst, int(cal["unlimited_budget"]), make_team("cooperative"), statics=st, seed=k)
        T.append(_time_to_fraction(log, inst.n_victims, float(cal["rescue_fraction_target"])))
    T = np.array(T)
    T90 = quantile(T, float(cal["quantile"]), cal["quantile_method"])
    H = math.ceil(T90 / float(cal["time_slack"])) if math.isfinite(T90) else None
    return {"H_max": H_max, "T": T, "T90": T90, "H": H, "n_never": int(np.sum(~np.isfinite(T)))}


def step2_bref(cfg: dict[str, Any], insts, cal: dict[str, Any], H: int) -> dict[str, Any]:
    """Step 2: B_ref = q90 of per-agent consumption (unlimited budget, horizon H); also verifies step 1."""
    env = RescueEnv(cfg, horizon=H, b_ref=1)
    u, reached, rf = [], [], []
    frac = float(cal["rescue_fraction_target"])
    for k, (inst, st) in enumerate(insts):
        log = run_episode(env, inst, int(cal["unlimited_budget"]), make_team("cooperative"), statics=st, seed=k)
        u.extend(np.sum(log.costs, axis=0).tolist() if log.costs else [0] * env.n)
        reached.append(env.n_rescued >= math.ceil(frac * inst.n_victims - 1e-9))
        rf.append(env.n_rescued / inst.n_victims)
    u = np.array(u, dtype=float)
    B_ref = int(round(quantile(u, float(cal["quantile"]), cal["quantile_method"])))
    return {"consumption": u, "B_ref": B_ref, "u_mean": float(u.mean()), "u_median": float(np.median(u)),
            "share_reaching_90pct_within_H": float(np.mean(reached)), "rf_unlimited": float(np.mean(rf))}


def analytic_bref(cfg: dict[str, Any], insts) -> dict[str, float]:
    """Step 3 (spec §4): back-of-envelope per-agent need from geometry, density and costs (expected values)."""
    e, c = cfg["env"], cfg["costs"]
    L, n = int(e["grid_size"]), int(e["n_agents"])
    p = float(e["p_heavy"])
    A = float(np.mean([st.n_free for _, st in insts]))                      # free cells (measured mean)
    h = float(np.mean([np.sum(inst.grid == 2) / st.n_free for inst, st in insts]))  # hazard share of free cells
    V = float(np.mean([inst.n_victims for inst, _ in insts]))
    w = 2 * int(e["radius_search"]) + 1
    c_m = 1.0 + h * (int(c["move_hazard"]) - int(c["move"]))               # mean entry cost (= 1 + h with 1/2 costs)
    N_S = A / w ** 2
    D = A / w
    C_V = V * ((1 - p) * int(c["rescue"]) + p * (int(c["rescue"]) + int(c["assist"])))
    D_h = p * V * (L / 2)
    B = (int(c["search"]) * N_S + c_m * (D + D_h)) / n + C_V / n
    return {"A_free": A, "hazard_share": h, "V": V, "N_S": N_S, "D": D, "D_h": D_h, "C_V": C_V, "c_m": c_m,
            "B_ref_analytic": B}


def pilot_sweep(cfg: dict[str, Any], insts, H: int, B_ref: int, rhos: list[float],
                policies: list[str]) -> list[dict[str, Any]]:
    """Step 4: per instance x rho x policy outcomes (RF, termination, feasibility, steps)."""
    cm = CostModel.from_config(cfg)
    n = int(cfg["env"]["n_agents"])
    rows = []
    for rho in rhos:
        b0 = initial_budget(rho, B_ref)
        env = RescueEnv(cfg, horizon=H, b_ref=B_ref)
        for k, (inst, st) in enumerate(insts):
            feas = bool(feasible_victims(inst, st, cm, n, H, "per_agent", b0).any())
            for name in policies:
                pol = OraclePolicy() if name == "oracle" else make_team(name)
                log = run_episode(env, inst, b0, pol, statics=st, seed=k)
                rows.append({"rho": rho, "b0": b0, "instance": k, "policy": name, "rescued": env.n_rescued,
                             "V": inst.n_victims, "rf": env.n_rescued / inst.n_victims,
                             "termination": log.termination, "steps": log.steps, "feasible": feas,
                             "spent": float(np.sum(log.costs)) if log.costs else 0.0})
    return rows


def _dist_to(x: float, target: float | tuple[float, float]) -> float:
    if isinstance(target, (tuple, list)):
        lo, hi = target
        return 0.0 if lo <= x <= hi else min(abs(x - lo), abs(x - hi))
    return abs(x - target)


def select_levels(rf_coop: dict[float, float], oracle_feasible: dict[float, float], sel: dict[str, Any]
                  ) -> dict[str, Any]:
    """Apply the pre-stated selection rules (config/calibration.yaml `selection`). Returns levels and an audit trail."""
    grid = sorted(rf_coop, reverse=True)
    trail = []

    def pick(cands: list[float], target) -> float:
        # tie-break: larger rho (candidates are scanned in decreasing rho and only a strictly better one replaces)
        best = None
        for r in sorted(cands, reverse=True):
            d = _dist_to(rf_coop[r], target)
            if best is None or d < best[1] - 1e-12:
                best = (r, d)
        return best[0]

    abundant = float(sel["abundant"])
    moderate = pick([r for r in grid if r < abundant], float(sel["moderate_target"]))
    scarce = pick([r for r in grid if r < moderate], float(sel["scarce_target"]))
    critical = pick([r for r in grid if r < scarce], tuple(sel["critical_band"]))
    trail.append(f"initial critical = {critical} (coop RF {rf_coop[critical]:.3f}, oracle>=1 share "
                 f"{oracle_feasible[critical]:.3f})")
    violation = False
    while oracle_feasible[critical] < float(sel["critical_min_oracle_feasible"]):
        higher = [r for r in grid if critical < r < scarce]
        if not higher:
            violation = True
            trail.append("no rho below Scarce satisfies the Critical feasibility constraint - VIOLATION reported")
            break
        critical = min(higher)
        trail.append(f"moved critical up to {critical} (oracle>=1 share {oracle_feasible[critical]:.3f})")
    return {"abundant": abundant, "moderate": moderate, "scarce": scarce, "critical": critical,
            "critical_constraint_violated": violation, "trail": trail}
