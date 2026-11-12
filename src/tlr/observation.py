"""Agent views, the compact observation tuple (f1..f5), its integer encoding, and action masking.

Implements: spec §1.7 (features, budget-bucket rule) and §1.3a (information use).

Information discipline (spec §1.3a): every function here takes an `AgentView`, which the environment builds ONLY from
what the agent has observed (its memory, its current view, co-located/nearby teammates, its spendable budget, t) plus
the static map (known a priori). Nothing in this module can access ground-truth victim status, so neither the
observation nor the mask can leak hidden information. Tests check this property directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from .costs import Action, CostModel, N_ACTIONS
from .mapgen import MapStatics

# Feature cardinalities (spec §1.7). Order matters: it defines the integer encoding.
F1_N, F2_N, F3_N, F4_N, F5_N = 11, 5, 6, 4, 3
N_OBS = F1_N * F2_N * F3_N * F4_N * F5_N  # 3,960

# f1 codes
F1_NONE, F1_HERE_LIGHT, F1_HERE_HEAVY = 0, 1, 2   # 3 + 2*dir + far for remote victims, dir in 0..3 (UP,DOWN,LEFT,RIGHT)
# f2 codes: 0 none, 1 + dir
# f3 codes: 0 none in range, 1 same cell, 2 + dir


@dataclass
class AgentView:
    """Everything agent i may legitimately use at step t (spec §1.3a).

    `known` maps cell -> (victim id, is_heavy) for victims the agent BELIEVES are still waiting. It is the agent's own
    memory: correct for cells currently in view, possibly stale elsewhere. `teammates` lists (agent id, cell) of
    teammates within Chebyshev radius r_tm (identity is available to scripted baselines' conventions; the learner's
    feature f3 drops it).

    Budgets: `spendable` is what the agent can actually spend (own budget, or the shared pool in the pooled
    ablation) and is used for masking. `budget_feature_value` is what feature f4 encodes (own budget, or the
    per-capita share floor(pool / n) in the pooled ablation). They are deliberately separate fields (spec §1.5, P4).
    """

    agent_id: int
    pos: int
    t: int
    horizon: int
    spendable: int
    budget_feature_value: int
    known: dict[int, tuple[int, bool]]
    observed: np.ndarray
    teammates: list[tuple[int, int]]


def budget_thresholds(b_ref: int, c_rescue: int) -> tuple[int, int, int]:
    """Integer thresholds (tau1, tau2, tau3) of the f4 rule (spec §1.7).

    tau1 = c_R; tau2 = max(tau1 + 1, ceil(0.25 * B_ref)); tau3 = max(tau2 + 1, ceil(0.5 * B_ref)).
    ceil is computed in integer arithmetic (-(-a // b)) to avoid floating-point error at exact boundaries.
    """
    if b_ref < 1:
        raise ValueError("B_ref must be a positive integer")
    tau1 = int(c_rescue)
    tau2 = max(tau1 + 1, -(-b_ref // 4))
    tau3 = max(tau2 + 1, -(-b_ref // 2))
    return tau1, tau2, tau3


def budget_bucket(b: int, thresholds: tuple[int, int, int]) -> int:
    """f4: half-open buckets [0,tau1), [tau1,tau2), [tau2,tau3), [tau3,inf). Boundary values go to the upper bucket."""
    if b < 0:
        raise ValueError("budget must be non-negative (masking guarantees this)")
    tau1, tau2, tau3 = thresholds
    if b < tau1:
        return 0
    if b < tau2:
        return 1
    if b < tau3:
        return 2
    return 3


def time_bucket(t: int, horizon: int) -> int:
    """f5: 0 if t < H/3, 1 if H/3 <= t < 2H/3, else 2 (integer arithmetic, so boundaries are exact)."""
    if 3 * t < horizon:
        return 0
    if 3 * t < 2 * horizon:
        return 1
    return 2


def _dominant_dir(L: int, src: int, dst: int) -> int:
    """Direction index (0 UP, 1 DOWN, 2 LEFT, 3 RIGHT) of the dominant axis from src to dst; ties -> vertical."""
    r1, c1 = divmod(src, L)
    r2, c2 = divmod(dst, L)
    dr, dc = r2 - r1, c2 - c1
    if abs(dr) >= abs(dc):
        return 0 if dr < 0 else 1
    return 2 if dc < 0 else 3


def nearest_known_victim(view: AgentView, st: MapStatics) -> tuple[int, int, bool, int] | None:
    """The f1 target: nearest believed-waiting victim by (cost, steps, cell index), or None.

    Returns (cell, victim id, is_heavy, steps). Uses only the agent's memory (possibly stale), never ground truth.
    """
    pos = view.pos
    best = None
    for cell, (vid, heavy) in view.known.items():
        key = (int(st.dist[pos, cell]), int(st.steps[pos, cell]), int(cell))
        if best is None or key < best[0]:
            best = (key, cell, vid, heavy)
    if best is None:
        return None
    (_, steps, _), cell, vid, heavy = best
    return int(cell), int(vid), bool(heavy), int(steps)


def features(view: AgentView, st: MapStatics, thresholds: tuple[int, int, int], near_steps: int) -> tuple[int, ...]:
    """Compute (f1, f2, f3, f4, f5) from the agent's view only."""
    pos = view.pos

    # f1: nearest believed-waiting victim by (cost, steps, cell index) - fully deterministic.
    f1 = F1_NONE
    tgt = nearest_known_victim(view, st)
    if tgt is not None:
        cell, _vid, heavy, steps = tgt
        if cell == pos:
            f1 = F1_HERE_HEAVY if heavy else F1_HERE_LIGHT
        else:
            f1 = 3 + 2 * int(st.first_move[pos, cell]) + (1 if steps > near_steps else 0)

    # f2: first step towards the cheapest-to-reach never-observed free cell (ties -> lowest cell index).
    unobs = np.flatnonzero(st.free & ~view.observed)
    if unobs.size == 0:
        f2 = 0
    else:
        target = int(unobs[int(np.argmin(st.dist[pos, unobs]))])
        f2 = 1 + int(st.first_move[pos, target])

    # f3: nearest teammate within r_tm (Manhattan, ties -> lower agent id); identity is dropped.
    f3 = 0
    if view.teammates:
        L = st.L
        pr, pc = divmod(pos, L)
        def manhattan(item: tuple[int, int]) -> tuple[int, int]:
            r, c = divmod(item[1], L)
            return (abs(r - pr) + abs(c - pc), item[0])
        _, tcell = min(view.teammates, key=manhattan)
        f3 = 1 if tcell == pos else 2 + _dominant_dir(L, pos, tcell)

    f4 = budget_bucket(view.budget_feature_value, thresholds)
    f5 = time_bucket(view.t, view.horizon)
    return (f1, f2, f3, f4, f5)


def encode(f: Sequence[int]) -> int:
    """Mixed-radix encoding of (f1..f5) into a single row index of the Q-table, in [0, N_OBS)."""
    f1, f2, f3, f4, f5 = f
    return (((f1 * F2_N + f2) * F3_N + f3) * F4_N + f4) * F5_N + f5


def decode(o: int) -> tuple[int, int, int, int, int]:
    """Inverse of `encode`."""
    o, f5 = divmod(int(o), F5_N)
    o, f4 = divmod(o, F4_N)
    o, f3 = divmod(o, F3_N)
    f1, f2 = divmod(o, F2_N)
    return (f1, f2, f3, f4, f5)


def compute_mask(view: AgentView, st: MapStatics, costs: CostModel) -> np.ndarray:
    """Valid-action mask (spec §1.2), from the agent's view only. WAIT is always valid.

    Uses `view.spendable` (own budget, or the actual team pool) - never the per-capita feature value.
    The own cell is always inside the agent's current view, so `view.known` is ground truth for `view.pos`.
    """
    m = np.zeros(N_ACTIONS, dtype=bool)
    b = view.spendable
    pos = view.pos
    for a in range(4):
        tgt = st.move_target[pos, a]
        if tgt >= 0 and st.entry_cost[tgt] <= b:
            m[a] = True
    m[Action.SEARCH] = costs.search <= b
    here = view.known.get(pos)
    if here is not None:
        m[Action.RESCUE] = costs.rescue <= b
        if here[1] and any(cell == pos for _, cell in view.teammates):
            m[Action.ASSIST] = costs.assist <= b
    m[Action.WAIT] = True
    return m
