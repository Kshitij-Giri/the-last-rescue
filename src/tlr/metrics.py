"""Performance metrics, diagnostics and the per-episode record (one row per episode in every results CSV).

Implements: spec §3 "Performance metrics" and the E3 conflict definition, plus spec §1.3a diagnostics
(stale corrections, stale travel). Everything is recomputed from the EpisodeLog and the instance, never from
environment internals, so verify_results.py (Phase 6) can recompute any table from raw logs.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from .costs import Action, CostModel
from .cooperation_metrics import cooperation_metrics, ratio
from .env import EpisodeLog
from .mapgen import Instance, MapStatics

A = Action


def coverage_from_log(log: EpisodeLog, st: MapStatics, r_v: int) -> float:
    """Fraction of free cells observed by any agent: passive views at every position held, plus SEARCH footprints."""
    seen = np.zeros(st.L * st.L, dtype=bool)
    for p in log.positions:
        for cell in p:
            seen[st.views[r_v][int(cell)]] = True
    for e in log.events:
        if e["type"] == "search":
            seen[e["footprint"]] = True
    return float((seen & st.free).sum()) / st.n_free


def stale_diagnostics(log: EpisodeLog) -> dict[str, float]:
    """stale corrections (memory wrong for >= 1 step), and stale travel: moves made while the agent's f1 target was already rescued (ground truth,
    used offline only). A victim rescued at step t is gone from step t+1 on."""
    rescue_t = {e["victim"]: e["t"] for e in log.events if e["type"] == "rescue"}
    moves = cost = 0
    for k in range(log.steps):
        for i in range(log.n_agents):
            v = int(log.f1_targets[k][i])
            if v >= 0 and v in rescue_t and rescue_t[v] < k and int(log.effective_actions[k][i]) <= A.RIGHT:
                moves += 1
                cost += int(log.costs[k][i])
    # A correction with steps_since_rescue = 0 means the agent saw the rescue happen in the same step: its memory was
    # never wrong at a decision time, so it is not counted as stale (the event is still logged).
    return {"stale_corrections": sum(1 for e in log.events
                                     if e["type"] == "stale_correction" and e["steps_since_rescue"] >= 1),
            "stale_travel_moves": moves, "stale_travel_cost": cost}


def performance_metrics(inst: Instance, st: MapStatics, log: EpisodeLog, r_v: int) -> dict[str, Any]:
    """Rescue outcomes, returns, efficiency, coverage, termination."""
    resc = [e for e in log.events if e["type"] == "rescue"]
    V = inst.n_victims
    rescued = len(resc)
    rewards = np.sum(log.rewards, axis=0) if log.rewards else np.zeros(log.n_agents)
    spent = float(np.sum(log.costs)) if log.costs else 0.0
    out: dict[str, Any] = {
        "V": V, "n_heavy": int(inst.victim_heavy.sum()),
        "rescued": rescued, "rescued_light": sum(1 for e in resc if not e["heavy"]),
        "rescued_heavy": sum(1 for e in resc if e["heavy"]),
        "rf": rescued / V if V else math.nan, "ms": int(rescued == V),
        "collective_return": float(rewards.sum()),
        "spent": spent, "efficiency_per100": ratio(100.0 * rescued, spent),
        "coverage": coverage_from_log(log, st, r_v),
        "termination": log.termination, "steps": log.steps,
        "budget_limited": int(log.termination == "exhausted"), "time_limited": int(log.termination == "horizon"),
        "failed_rescue": sum(1 for e in log.events if e["type"] == "failed_rescue"),
        "failed_assist": sum(1 for e in log.events if e["type"] == "failed_assist"),
        "preempted": sum(1 for e in log.events if e["type"] == "preempted"),
    }
    for i, r in enumerate(rewards):
        out[f"return_agent{i}"] = float(r)
    out.update(stale_diagnostics(log))
    return out


def episode_record(inst: Instance, st: MapStatics, log: EpisodeLog, costs: CostModel, r_v: int,
                   **labels: Any) -> dict[str, Any]:
    """One flat row: labels (method, condition, seed, instance...) + performance + cooperation metrics."""
    row: dict[str, Any] = dict(labels)
    row["instance_seed"] = inst.seed
    row.update(performance_metrics(inst, st, log, r_v))
    row.update(cooperation_metrics(inst, st, log, costs))
    return row


def e3_conflict_flags(rows: list[dict[str, Any]], n_agents: int) -> list[int]:
    """E3 (spec §3 as clarified in P6): within one group of episodes (`rows` = one condition), flag an episode iff
    (a) its best agent's individual return is ABOVE the median of all individual returns in the group, and
    (b) its collective return is BELOW the group median of collective returns.
    i.e. an individually successful agent on an under-performing team. (The v0.2 wording, "best agent on a below-median
    team", was true of every below-median team and therefore flagged ~50% of episodes by construction.)
    Returns 1/0 per row."""
    if not rows:
        return []
    ind = np.array([[r[f"return_agent{i}"] for i in range(n_agents)] for r in rows], dtype=float)
    coll = np.array([r["collective_return"] for r in rows], dtype=float)
    med_ind, med_coll = float(np.median(ind)), float(np.median(coll))
    return [int(ind[k].max() > med_ind and coll[k] < med_coll) for k in range(len(rows))]
