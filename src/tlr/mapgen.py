"""Map/instance generation, exact cheapest-path tables, and the exact instance-feasibility check.

Implements:
- spec §1.1 / §1.8: static map M (FREE, WALL, HAZARD cells, base b), victims with types, connectivity guarantee;
- spec §1.7: cheapest-path distances and FIRST-STEP directions used by observation features f1/f2;
- spec §1.4: exact feasibility of an instance at given budgets ("can a full-information planner rescue >= 1 victim").

Cells are addressed by a flat index k = row * L + col. Row 0 is the north (top) edge.
Path cost convention: d(a, b) = sum of the ENTRY costs of every cell entered on the way from a to b (the start cell is
not paid for). Entry cost is costs.move for FREE cells and costs.move_hazard for HAZARD cells. Therefore d is not
symmetric when a or b is a hazard cell, which matches how the environment charges moves.
"""

from __future__ import annotations

import heapq
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Sequence

import numpy as np

from .costs import Action, CostModel, MOVE_ACTIONS, MOVE_DELTAS
from .utils import make_rng, round_half_up

FREE, WALL, HAZARD = 0, 1, 2
INF = np.iinfo(np.int32).max // 4  # "unreachable" marker that cannot overflow when a small cost is added


@dataclass
class Instance:
    """One episode instance: a static map plus victim placements and types (ground truth)."""

    L: int
    grid: np.ndarray            # shape (L*L,), int8 in {FREE, WALL, HAZARD}
    base: int                   # flat index of the base cell (all agents start here)
    victim_cells: np.ndarray    # shape (V,), int64 flat indices (distinct)
    victim_heavy: np.ndarray    # shape (V,), bool
    seed: int | None = None     # generator seed (None for hand-written instances)
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def n_victims(self) -> int:
        return int(len(self.victim_cells))

    def rc(self, k: int) -> tuple[int, int]:
        """Flat index -> (row, col)."""
        return divmod(int(k), self.L)

    def to_bytes(self) -> bytes:
        """Canonical serialisation (for hashing in determinism tests and manifests)."""
        return (np.int64(self.L).tobytes() + self.grid.astype(np.int8).tobytes() + np.int64(self.base).tobytes()
                + self.victim_cells.astype(np.int64).tobytes() + self.victim_heavy.astype(np.int8).tobytes())


# --------------------------------------------------------------------------------------------------------------
# Generation
# --------------------------------------------------------------------------------------------------------------

def _connected_non_walls(grid: np.ndarray, L: int, start: int) -> bool:
    """True iff every non-wall cell is 4-connected to `start`."""
    seen = np.zeros(L * L, dtype=bool)
    seen[start] = True
    dq = deque([start])
    count = 1
    while dq:
        k = dq.popleft()
        r, c = divmod(k, L)
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            rr, cc = r + dr, c + dc
            if 0 <= rr < L and 0 <= cc < L:
                j = rr * L + cc
                if not seen[j] and grid[j] != WALL:
                    seen[j] = True
                    count += 1
                    dq.append(j)
    return count == int(np.sum(grid != WALL))


def generate_instance(cfg: dict[str, Any], seed: int) -> Instance:
    """Generate an instance deterministically from `seed` using the `env` block of `cfg`.

    The sequence of random draws does not depend on p_heavy (types are assigned from a permutation drawn for every
    instance), so the same seed with p_heavy = 0 and p_heavy = 0.5 yields the same layout and victim positions;
    only the types differ. This is what makes the A3 comparison paired (spec §5 A3).
    """
    e = cfg["env"]
    L = int(e["grid_size"])
    rng = make_rng(seed)

    # 1. Base: a random corner, offset by 0 or 1 in each direction (spec §1.8 "base in a corner region").
    corner = int(rng.integers(4))
    off_r, off_c = (int(x) for x in rng.integers(0, 2, size=2))
    br = off_r if corner in (0, 1) else L - 1 - off_r
    bc = off_c if corner in (0, 2) else L - 1 - off_c
    base = br * L + bc

    # 2. Walls: try candidate cells in a random order and keep a wall only if all non-wall cells stay connected.
    #    Every candidate is tried at most once, so this always terminates; the achieved count is recorded.
    grid = np.full(L * L, FREE, dtype=np.int8)
    n_walls_target = round_half_up(float(e["wall_fraction"]) * L * L)
    candidates = [k for k in rng.permutation(L * L).tolist() if k != base]
    n_walls = 0
    for k in candidates:
        if n_walls >= n_walls_target:
            break
        grid[k] = WALL
        if _connected_non_walls(grid, L, base):
            n_walls += 1
        else:
            grid[k] = FREE

    # 3. Hazards among free non-base cells.
    free_nonbase = np.array([k for k in range(L * L) if grid[k] == FREE and k != base], dtype=np.int64)
    n_haz = round_half_up(float(e["hazard_fraction"]) * len(free_nonbase))
    hazard_cells = rng.choice(free_nonbase, size=n_haz, replace=False) if n_haz > 0 else np.array([], dtype=np.int64)
    grid[hazard_cells] = HAZARD

    # 4. Victims on non-wall cells at Chebyshev distance >= min_cheb from the base (not visible at t = 0).
    min_cheb = int(e["victim_min_chebyshev_from_base"])
    eligible = np.array([k for k in range(L * L) if grid[k] != WALL
                         and max(abs(k // L - br), abs(k % L - bc)) >= min_cheb], dtype=np.int64)
    V = round_half_up(float(e["victim_density"]) * L * L)
    if V > len(eligible):
        raise ValueError(f"cannot place {V} victims on {len(eligible)} eligible cells")
    victim_cells = np.sort(rng.choice(eligible, size=V, replace=False)).astype(np.int64)
    n_heavy = round_half_up(float(e["p_heavy"]) * V)
    perm = rng.permutation(V)  # drawn regardless of p_heavy (see docstring)
    victim_heavy = perm < n_heavy

    meta = {"walls_target": n_walls_target, "walls_placed": n_walls, "hazards": int(n_haz), "V": int(V),
            "n_heavy": int(n_heavy)}
    return Instance(L=L, grid=grid, base=base, victim_cells=victim_cells, victim_heavy=victim_heavy,
                    seed=int(seed), meta=meta)


def instance_from_ascii(rows: Sequence[str]) -> Instance:
    """Build a hand-written instance (used by tests and scripted examples).

    Characters: '.' free, '#' wall, '~' hazard, 'B' base, 'l' light victim, 'h' heavy victim,
    'L' light victim on a hazard cell, 'H' heavy victim on a hazard cell.
    Victims are indexed in row-major order of appearance.
    """
    L = len(rows)
    if any(len(r) != L for r in rows):
        raise ValueError("ascii map must be square")
    grid = np.full(L * L, FREE, dtype=np.int8)
    base = -1
    cells: list[int] = []
    heavy: list[bool] = []
    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            k = r * L + c
            if ch == "#":
                grid[k] = WALL
            elif ch in "~LH":
                grid[k] = HAZARD
            if ch == "B":
                base = k
            if ch in "lhLH":
                cells.append(k)
                heavy.append(ch in "hH")
            if ch not in ".#~BlhLH":
                raise ValueError(f"unknown map character {ch!r}")
    if base < 0:
        raise ValueError("ascii map needs a base 'B'")
    if not _connected_non_walls(grid, L, base):
        raise ValueError("ascii map is not connected")
    return Instance(L=L, grid=grid, base=base, victim_cells=np.array(cells, dtype=np.int64),
                    victim_heavy=np.array(heavy, dtype=bool), seed=None, meta={"source": "ascii"})


# --------------------------------------------------------------------------------------------------------------
# Static per-map tables
# --------------------------------------------------------------------------------------------------------------

@dataclass
class MapStatics:
    """Everything about a map that never changes during an episode, precomputed once.

    Agents are allowed to know all of this (spec §1.3a: the static map is known a priori).
    """

    L: int
    free: np.ndarray            # (L*L,) bool: not a wall
    entry_cost: np.ndarray      # (L*L,) int64: cost of entering the cell (INF for walls)
    move_target: np.ndarray     # (L*L, 4) int64: target cell of UP/DOWN/LEFT/RIGHT, -1 if off-grid or wall
    dist: np.ndarray            # (L*L, L*L) int64: cheapest path cost d(a, b); INF if a or b is a wall
    steps: np.ndarray           # (L*L, L*L) int64: number of moves on the tie-broken cheapest path; INF if unreachable
    first_move: np.ndarray      # (L*L, L*L) int8: first action (0..3) on that path; -1 if a == b or unreachable
    views: dict[int, list[np.ndarray]]  # radius -> per-cell array of non-wall cells within that Chebyshev radius
    n_free: int


def compute_statics(inst: Instance, costs: CostModel, radii: Sequence[int]) -> MapStatics:
    """Precompute movement tables, all-pairs cheapest paths with deterministic tie-breaking, and view footprints."""
    L, N = inst.L, inst.L * inst.L
    free = inst.grid != WALL
    entry = np.where(inst.grid == HAZARD, costs.move_hazard, costs.move).astype(np.int64)
    entry[~free] = INF

    move_target = np.full((N, 4), -1, dtype=np.int64)
    for k in range(N):
        if not free[k]:
            continue
        r, c = divmod(k, L)
        for a in MOVE_ACTIONS:
            dr, dc = MOVE_DELTAS[a]
            rr, cc = r + dr, c + dc
            if 0 <= rr < L and 0 <= cc < L and free[rr * L + cc]:
                move_target[k, int(a)] = rr * L + cc

    dist = np.full((N, N), INF, dtype=np.int64)
    steps = np.full((N, N), INF, dtype=np.int64)
    first = np.full((N, N), -1, dtype=np.int8)
    free_idx = np.flatnonzero(free)
    for b in free_idx:
        # Reverse Dijkstra from target b: D(u) = min over neighbours v of entry(v) + D(v).
        D = np.full(N, INF, dtype=np.int64)
        D[b] = 0
        heap = [(0, int(b))]
        done = np.zeros(N, dtype=bool)
        order: list[int] = []
        while heap:
            dv, v = heapq.heappop(heap)
            if done[v]:
                continue
            done[v] = True
            order.append(v)
            cand = dv + entry[v]
            for u in move_target[v]:  # neighbours of v (the grid is undirected for adjacency)
                if u >= 0 and not done[u] and cand < D[u]:
                    D[u] = cand
                    heapq.heappush(heap, (int(cand), int(u)))
        dist[:, b] = D
        # Deterministic first step: the first action in the order UP, DOWN, LEFT, RIGHT that lies on a cheapest path.
        # Processing cells in increasing D guarantees the successor's step count is already known.
        steps[b, b] = 0
        for u in order[1:]:
            for a in range(4):
                v = move_target[u, a]
                if v >= 0 and entry[v] + D[v] == D[u]:
                    first[u, b] = a
                    steps[u, b] = steps[v, b] + 1
                    break

    radii_set = sorted(set(int(r) for r in radii))
    views: dict[int, list[np.ndarray]] = {}
    for rad in radii_set:
        per_cell: list[np.ndarray] = []
        for k in range(N):
            r, c = divmod(k, L)
            cells = [rr * L + cc
                     for rr in range(max(0, r - rad), min(L, r + rad + 1))
                     for cc in range(max(0, c - rad), min(L, c + rad + 1))
                     if free[rr * L + cc]]
            per_cell.append(np.array(cells, dtype=np.int64))
        views[rad] = per_cell

    return MapStatics(L=L, free=free, entry_cost=entry, move_target=move_target, dist=dist, steps=steps,
                      first_move=first, views=views, n_free=int(free.sum()))


# --------------------------------------------------------------------------------------------------------------
# Exact feasibility (spec §1.4)
# --------------------------------------------------------------------------------------------------------------

def feasible_victims(inst: Instance, st: MapStatics, costs: CostModel, n_agents: int, horizon: int,
                     budget_mode: str, b0: int) -> np.ndarray:
    """Boolean array: victim v can be rescued by a full-information planner starting from the base at t = 0.

    All agents start at the base, so the cheapest way for any agent to reach v costs d(base, c_v) and takes
    steps(base, c_v) moves; the rescue then happens on step index steps (0-based), which must be < H.
    per_agent: light needs one agent with d + c_R <= b0; heavy needs two distinct agents, one with d + c_R <= b0 and
    another with d + c_A <= b0 (budgets are equal, so this is d + max(c_R, c_A) <= b0 and n >= 2).
    pooled: one shared pool of b0_team = n * b0; light needs d + c_R <= pool, heavy needs 2d + c_R + c_A <= pool.
    Exact for "at least one victim": a single cheapest path is optimal for a single victim.
    """
    d = st.dist[inst.base, inst.victim_cells]
    s = st.steps[inst.base, inst.victim_cells]
    time_ok = (s + 1) <= horizon
    cR, cA = costs.c_rescue, costs.c_assist
    heavy = inst.victim_heavy
    if budget_mode == "per_agent":
        light_ok = d + cR <= b0
        heavy_ok = (n_agents >= 2) & (d + max(cR, cA) <= b0)
    elif budget_mode == "pooled":
        pool = n_agents * b0
        light_ok = d + cR <= pool
        heavy_ok = (n_agents >= 2) & (2 * d + cR + cA <= pool)
    else:
        raise ValueError(f"unknown budget mode {budget_mode!r}")
    return time_ok & np.where(heavy, heavy_ok, light_ok)


def is_feasible(inst: Instance, st: MapStatics, costs: CostModel, n_agents: int, horizon: int,
                budget_mode: str, b0: int) -> bool:
    """Instance feasibility at budget b0 (spec §1.4): at least one victim is rescuable."""
    return bool(feasible_victims(inst, st, costs, n_agents, horizon, budget_mode, b0).any())
