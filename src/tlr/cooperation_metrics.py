"""Cooperation metrics C1-C5 and individual-vs-collective events E1-E2, computed deterministically from an EpisodeLog.

Implements: spec §3 (formal definitions) with the clarification recorded as P6 in docs/deviations_log.md:
"minimal requirement" rule - each rescue event has exactly ONE effective RESCUE and (for heavy victims) ONE effective
ASSIST. Extra simultaneous RESCUEs/ASSISTs on the same victim are redundant co-actions (wasted, not cooperative).
When several agents share a role, the lowest-index one is the canonical participant (used for C5 converging moves).

Ratio metrics return numerator and denominator as well, so that per-seed values can be pooled over episodes
(preregistration §3: sum of numerators / sum of denominators). A ratio with denominator 0 is NaN (undefined).
None of these metrics uses rewards.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from .costs import Action, CostModel
from .env import EpisodeLog
from .mapgen import Instance, MapStatics

A = Action
THETA = 0.5  # redundancy threshold of C2 (spec §3)


def ratio(num: float, den: float) -> float:
    """num / den, or NaN when den == 0 (undefined, reported as missing)."""
    return float(num) / float(den) if den else math.nan


def gini(x: np.ndarray) -> float:
    """G = sum_i sum_j |x_i - x_j| / (2 n^2 mean(x)); 0 if mean is 0 (spec §3 C4b)."""
    x = np.asarray(x, dtype=float)
    n = len(x)
    m = x.mean() if n else 0.0
    if n == 0 or m == 0:
        return 0.0
    return float(np.abs(x[:, None] - x[None, :]).sum() / (2 * n * n * m))


def rescue_events(log: EpisodeLog) -> list[dict[str, Any]]:
    return [e for e in log.events if e["type"] == "rescue"]


def effective_assist_rate(log: EpisodeLog) -> dict[str, float]:
    """C1: effective ASSISTs (one per heavy rescue) / all ASSIST actions taken."""
    den = int(sum(int((a == A.ASSIST).sum()) for a in log.effective_actions))
    num = sum(1 for e in rescue_events(log) if e["heavy"])
    return {"ear_num": num, "ear_den": den, "ear": ratio(num, den)}


def redundant_search(log: EpisodeLog, theta: float = THETA) -> dict[str, float]:
    """C2: share of SEARCHes whose footprint was already >= theta covered by earlier SEARCHes.

    redundant_other: overlap with cells already covered by OTHER agents' searches >= theta (coordination failure).
      "Already covered by others" = their searches at earlier steps PLUS same-step searches of lower-index agents
      (P6: without this, identical simultaneous searches by several agents counted as zero redundancy, although all
      but one add no information; the lowest-index searcher of a step is treated as the first).
    redundant_self: overlap with the agent's OWN searches at earlier steps >= theta, and not redundant_other.
    """
    searches = sorted((e for e in log.events if e["type"] == "search"), key=lambda e: (e["t"], e["agent"]))
    covered: dict[int, set[int]] = {i: set() for i in range(log.n_agents)}
    n_other = n_self = 0
    k = 0
    while k < len(searches):
        t = searches[k]["t"]
        batch = [e for e in searches[k:] if e["t"] == t]
        same_step_lower: set[int] = set()
        for e in batch:  # batch is sorted by agent index
            i, F = e["agent"], set(e["footprint"])
            others = set().union(*(covered[j] for j in covered if j != i)) | same_step_lower
            same_step_lower |= F
            if len(F & others) / len(F) >= theta:
                n_other += 1
            elif len(F & covered[i]) / len(F) >= theta:
                n_self += 1
        for e in batch:
            covered[e["agent"]] |= set(e["footprint"])
        k += len(batch)
    den = len(searches)
    return {"rsr_den": den, "rsr_other_num": n_other, "rsr_self_num": n_self,
            "rsr": ratio(n_other + n_self, den), "rsr_other": ratio(n_other, den), "rsr_self": ratio(n_self, den)}


def territory_division(log: EpisodeLog, base: int) -> dict[str, float]:
    """C3: TDI = 1 - mean pairwise Jaccard overlap of visited-cell sets (base excluded); J = 0 if both sets empty."""
    n = log.n_agents
    U = [set(int(p[i]) for p in log.positions) - {int(base)} for i in range(n)]
    if n < 2:
        return {"tdi": math.nan}
    js = []
    for i in range(n):
        for j in range(i + 1, n):
            union = U[i] | U[j]
            js.append(len(U[i] & U[j]) / len(union) if union else 0.0)
    return {"tdi": 1.0 - float(np.mean(js))}


def resource_use(log: EpisodeLog, costs: CostModel) -> dict[str, float]:
    """C4a productive spend share (minimal required action costs of completed rescues / total spent);
    C4b Gini of per-agent consumption (sum of costs each agent paid) and of remaining budgets (per-agent mode only)."""
    paid = np.sum(log.costs, axis=0) if log.costs else np.zeros(log.n_agents)
    total = float(paid.sum())
    num = sum(costs.rescue + (costs.assist if e["heavy"] else 0) for e in rescue_events(log))
    out = {"pss_num": float(num), "pss_den": total, "pss": ratio(num, total), "gini_consumption": gini(paid)}
    out["gini_remaining"] = gini(log.budgets[-1]) if log.budget_mode == "per_agent" else math.nan
    return out


def cooperation_rate(log: EpisodeLog, st: MapStatics) -> dict[str, float]:
    """C5: cooperative non-WAIT actions / non-WAIT actions (effective actions).

    Cooperative = per heavy rescue at (t*, c): the canonical RESCUE and the canonical ASSIST, plus every move of a
    canonical participant during [t* - 2L, t*) that reduced its cheapest-path cost to c.
    """
    L = st.L
    nonwait = int(sum(int((a != A.WAIT).sum()) for a in log.effective_actions))
    coop: set[tuple[int, int]] = set()
    for e in rescue_events(log):
        if not e["heavy"]:
            continue
        t_star, c = e["t"], e["cell"]
        r, a = min(e["rescuers"]), min(e["assisters"])
        coop.add((t_star, r))
        coop.add((t_star, a))
        for p in (r, a):
            for t in range(max(0, t_star - 2 * L), t_star):
                act = int(log.effective_actions[t][p])
                if act <= A.RIGHT and st.dist[log.positions[t][p], c] > st.dist[log.positions[t + 1][p], c]:
                    coop.add((t, p))
    return {"cr_num": len(coop), "cr_den": nonwait, "cr": ratio(len(coop), nonwait)}


def exp4_events(log: EpisodeLog) -> dict[str, float]:
    """E1 abandonment: failed RESCUE/ASSIST while >= 1 other agent stood on the same cell (its non-complementary action
    wasted the partner's). E2: wasted duplicate light RESCUEs."""
    e1 = 0
    for e in log.events:
        if e["type"] in ("failed_rescue", "failed_assist"):
            if int(np.sum(log.positions[e["t"]] == e["cell"])) >= 2:
                e1 += 1
    e2 = sum(e["n_wasted"] for e in log.events if e["type"] == "duplicate_rescue")
    return {"e1_abandonment": e1, "e2_duplicate": e2}


def cooperation_metrics(inst: Instance, st: MapStatics, log: EpisodeLog, costs: CostModel) -> dict[str, float]:
    """All C1-C5 and E1-E2 values of one episode."""
    out: dict[str, float] = {}
    out.update(effective_assist_rate(log))
    out.update(redundant_search(log))
    out.update(territory_division(log, inst.base))
    out.update(resource_use(log, costs))
    out.update(cooperation_rate(log, st))
    out.update(exp4_events(log))
    return out
